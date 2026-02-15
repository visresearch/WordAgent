"""
文档处理 Agent - 使用 LangGraph ReAct 单一智能体 + 流式输出
"""

import asyncio
import concurrent.futures
import json
import traceback
from collections.abc import AsyncGenerator

from langchain_core.messages import AIMessageChunk, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, MessagesState, StateGraph

from app.services.llm_client import LLMClientManager, resolve_model
from app.services.agent.prompts import get_agent_prompt
from app.services.agent.tools import (
    ALL_TOOLS,
    TOOL_MAP,
    _current_chat_id,
    register_loop,
    read_document,
)


# region Create LLM


def create_llm(model_name: str):
    """创建 LLM 实例，根据提供商类型返回对应的 Chat 实例"""
    from app.services.llm_client import get_temperature

    provider_info = LLMClientManager.get_provider_info(model_name)

    from langchain_openai import ChatOpenAI
    from app.services.llm_client import get_https_proxy_url, get_http_proxy_url

    # 获取代理配置
    proxy_url = get_https_proxy_url() or get_http_proxy_url()
    http_client = None
    http_async_client = None
    if proxy_url:
        import httpx

        http_client = httpx.Client(proxy=proxy_url)
        http_async_client = httpx.AsyncClient(proxy=proxy_url)

    return ChatOpenAI(
        model=model_name,
        openai_api_key=provider_info.api_key,
        openai_api_base=provider_info.base_url,
        temperature=get_temperature(),
        streaming=True,
        http_client=http_client,
        http_async_client=http_async_client,
    )


# region LangGraph Agent（ReAct）


def build_graph(llm_with_tools):
    """
    构建 LangGraph ReAct 工作流（单一智能体）

    流程：
    START -> agent -> (有 tool_calls?) -> tools -> agent -> ... -> END
                   -> (无 tool_calls) -> END

    agent 自动循环调用工具，直到不再需要工具为止。
    """
    graph = StateGraph(MessagesState)

    # ---- 节点 ----

    def agent_node(state: MessagesState) -> dict:
        """单一 Agent 节点 - 决定下一步行动或直接回复"""
        print("[Agent] 开始处理")
        response = llm_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    def tools_node(state: MessagesState) -> dict:
        """工具执行节点 - 执行 Agent 请求的所有工具"""
        last_message = state["messages"][-1]
        results = []

        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            print(f"[Tools] 执行工具: {tool_name}")

            tool_fn = TOOL_MAP.get(tool_name)
            if tool_fn:
                result = tool_fn.invoke(tool_call["args"])
                # 标准化结果为字符串
                if isinstance(result, dict):
                    content = json.dumps(result, ensure_ascii=False)
                elif isinstance(result, str):
                    content = result
                else:
                    content = str(result)
                results.append(ToolMessage(content=content, tool_call_id=tool_call["id"], name=tool_name))
            else:
                print(f"[Tools] ⚠️ 未知工具: {tool_name}")
                results.append(
                    ToolMessage(content=f"错误: 未知工具 {tool_name}", tool_call_id=tool_call["id"], name=tool_name)
                )

        return {"messages": results}

    # ---- 路由 ----

    def should_continue(state: MessagesState) -> str:
        """判断 Agent 是否还需要调用工具"""
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            print("[Router] -> tools")
            return "tools"
        print("[Router] -> END")
        return END

    # ---- 构建图 ----

    graph.add_node("agent", agent_node)
    graph.add_node("tools", tools_node)

    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")  # 工具执行完毕，始终回到 Agent

    return graph.compile()


# region 主处理函数


async def process_writing_request_stream(
    message: str,
    document_range: list[dict] | None = None,
    history: list | None = None,
    model: str | None = None,
    mode: str | None = None,
    chat_id: str | None = None,
) -> AsyncGenerator[str, None]:
    """
    使用 LangGraph ReAct Agent 处理写作请求（流式输出）

    Args:
        message: 用户消息
        document_range: 文档范围列表 [{startPos: int, endPos: int}, ...]
        history: 历史消息
        model: 用户选择的模型
        mode: 对话模式（agent/ask）
        chat_id: WebSocket 会话 ID（用于工具回调）

    Yields:
        SSE 格式的流式输出
    """
    print("[Agent] 开始处理请求")
    print(f"[Agent] 模式: {mode}")

    model_name = resolve_model(model or "auto")
    llm = create_llm(model_name)

    # 根据模式决定绑定哪些工具
    is_ask_mode = mode == "ask"

    if is_ask_mode:
        tools = [read_document]
        print("[Agent] ask 模式，已绑定 read_document")
    else:
        tools = ALL_TOOLS
        print(f"[Agent] agent 模式，已绑定 {[t.name for t in tools]}")

    llm_with_tools = llm.bind_tools(tools)
    app = build_graph(llm_with_tools)

    try:
        from datetime import datetime

        weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        now = datetime.now()
        current_time = now.strftime("%Y年%m月%d日 %H:%M") + " " + weekdays[now.weekday()]
        system_prompt = get_agent_prompt() + f"\n\n# 当前时间\n{current_time}"
        messages = [SystemMessage(content=system_prompt)]

        # 构建用户消息
        user_content = message
        if document_range:
            # 有文档范围时，指示 agent 调用 read_document 读取这些范围
            range_instructions = "\n".join(
                f"  - read_document(startPos={r.get('startPos', -1)}, endPos={r.get('endPos', -1)})"
                for r in document_range
            )
            user_content = (
                f"用户要求：{message}\n\n"
                f"⚠️ 请先调用 read_document 工具读取以下文档范围（必须调用，不可跳过）：\n{range_instructions}\n"
                f"读取到文档内容后，根据用户要求进行处理，并调用 generate_document 工具输出结果。"
            )
            print(f"[Agent] 文档范围: {document_range}")

        messages.append(HumanMessage(content=user_content))

        print(f"[Agent] 消息数量: {len(messages)}")

        # 获取事件循环，注册供 tool 使用
        loop = asyncio.get_running_loop()
        if chat_id:
            register_loop(chat_id, loop)

        # 队列用于线程间传递流式数据
        queue: asyncio.Queue = asyncio.Queue()
        has_tool_result = False
        generating_notified = False  # 是否已通知前端"正在生成文档"

        def run_stream():
            """在独立线程中运行同步的 LangGraph stream"""
            try:
                if chat_id:
                    _current_chat_id.set(chat_id)

                response = app.stream(
                    {"messages": messages},
                    stream_mode=["messages", "custom"],
                )

                for stream_item in response:
                    asyncio.run_coroutine_threadsafe(queue.put(stream_item), loop)

                asyncio.run_coroutine_threadsafe(queue.put(None), loop)
            except Exception as e:
                asyncio.run_coroutine_threadsafe(queue.put(("error", str(e))), loop)

        # 在线程池中启动
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        executor.submit(run_stream)

        # 从队列中消费流式数据
        while True:
            stream_item = await queue.get()

            if stream_item is None:
                break

            if isinstance(stream_item, tuple) and stream_item[0] == "error":
                raise Exception(stream_item[1])

            if not isinstance(stream_item, tuple):
                continue

            input_type, chunk = stream_item

            if input_type == "messages":
                if not chunk or len(chunk) == 0:
                    continue
                msg = chunk[0]
                content = msg.content

                # 检测 LLM 开始生成 generate_document 的 tool_call 参数
                if isinstance(msg, AIMessageChunk) and not generating_notified:
                    tool_call_chunks = getattr(msg, "tool_call_chunks", [])
                    for tc in tool_call_chunks:
                        if tc.get("name") == "generate_document":
                            generating_notified = True
                            print("[Agent] 📝 检测到 LLM 开始生成文档")
                            yield f"data: {json.dumps({'type': 'generate_document', 'content': '📝 正在生成文档'}, ensure_ascii=False)}\n\n"
                            break

                if isinstance(msg, ToolMessage):
                    # 根据工具名称决定是否转发给前端
                    tool_name = getattr(msg, "name", "")
                    has_tool_result = True

                    if tool_name == "read_document":
                        # read_document 结果是中间数据，不发给前端
                        print(f"[Agent] ⏭️ 跳过 read_document 工具返回值")
                        continue

                    if tool_name == "generate_document":
                        # generate_document 结果发给前端渲染
                        try:
                            doc_json = json.loads(content)
                            if "paragraphs" in doc_json:
                                print(f"[Agent] ✅ 提取到 generate_document 结果")
                                yield f"data: {json.dumps({'type': 'json', 'content': doc_json}, ensure_ascii=False)}\n\n"
                                continue
                        except json.JSONDecodeError:
                            pass

                    # 其他工具的结果，跳过
                    continue

                # 普通文本输出（Agent 的回复）
                if content:
                    yield f"data: {json.dumps({'type': 'text', 'content': content}, ensure_ascii=False)}\n\n"

            elif input_type == "custom":
                # stream_writer 的输出（工具的状态消息）
                print(f"[Agent] 自定义输出: {chunk}")
                if chunk:
                    if isinstance(chunk, dict):
                        yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                    else:
                        yield f"data: {json.dumps({'type': 'status', 'content': str(chunk)}, ensure_ascii=False)}\n\n"

        # 只在 agent 模式下且期望生成文档时显示警告
        if not has_tool_result and not is_ask_mode and document_range:
            yield f"data: {json.dumps({'type': 'status', 'content': '⚠️ 没有检测到调用工具，模型可能不支持'}, ensure_ascii=False)}\n\n"

        yield "data: [DONE]\n\n"

    except Exception as e:
        print(f"[Agent Error] {e}")
        traceback.print_exc()
        yield f"data: {json.dumps({'type': 'text', 'content': f'错误: {str(e)}'}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
