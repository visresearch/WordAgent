"""
文档处理 Agent - MainAgent + SubAgent 架构（Copilot 式独立上下文窗口）

架构设计：
- MainAgent：理解用户意图、调用搜索/读取/查询等工具，决定何时委派
- SubAgent：在独立上下文窗口中执行文档生成任务
  - 不继承 MainAgent 的消息历史
  - 有自己的专用系统提示（只关注文档生成）
  - 中间推理过程对 MainAgent 不可见
  - 只返回最终文档 JSON 给 MainAgent
"""

import asyncio
import concurrent.futures
import json
import traceback
from collections.abc import AsyncGenerator

from langchain_core.messages import AIMessageChunk, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, MessagesState, StateGraph

from app.services.llm_client import LLMClientManager, resolve_model
from app.services.agent.prompts import get_agent_prompt, get_subagent_prompt
from app.services.agent.tools import (
    MAIN_TOOLS,
    TOOL_MAP,
    SUBAGENT_TOOLS,
    SUBAGENT_TOOL_MAP,
    _current_chat_id,
    register_loop,
    read_document,
)


# region Create LLM


def create_llm(model_name: str):
    """创建 LLM 实例，根据提供商类型返回对应的 Chat 实例"""
    import os

    from app.services.llm_client import get_temperature

    provider_info = LLMClientManager.get_provider_info(model_name)

    from langchain_openai import ChatOpenAI
    from app.services.llm_client import get_https_proxy_url, get_http_proxy_url

    # 获取代理配置
    proxy_url = get_https_proxy_url() or get_http_proxy_url()

    # 当用户未启用代理时，临时清除环境变量中的代理设置
    # 防止 openai/httpx 读取到系统的 socks:// 代理导致 scheme 不支持报错
    _proxy_env_keys = [
        "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
        "http_proxy", "https_proxy", "all_proxy",
    ]
    saved_env = {}
    if not proxy_url:
        for key in _proxy_env_keys:
            if key in os.environ:
                saved_env[key] = os.environ.pop(key)

    try:
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
    finally:
        # 恢复环境变量
        os.environ.update(saved_env)


# region SubAgent (独立上下文窗口)


def _try_parse_tool_args(raw_args: str) -> dict | None:
    """修复被截断的 tool_call JSON 参数（解决 invalid_tool_calls 问题）

    处理以下截断场景：
    1. 字符串中间截断：{"text": "一些内容被截 → 补 " 再关闭括号
    2. 转义序列中间截断：{"text": "hello \ → 去掉不完整的 \ 再补 "
    3. 不完整键值对：{"key": → 补 null
    4. 尾部逗号：{"a": 1, → 去掉逗号再关闭
    """
    if not raw_args:
        return None
    try:
        return json.loads(raw_args)
    except json.JSONDecodeError:
        pass

    # 用栈追踪 JSON 结构状态（正确的关闭顺序）
    stack = []  # 记录未闭合的 '{' 和 '[' 的顺序
    in_string = False
    escape = False
    for ch in raw_args:
        if escape:
            escape = False
            continue
        if ch == '\\' and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == '{':
            stack.append('{')
        elif ch == '}':
            if stack and stack[-1] == '{':
                stack.pop()
        elif ch == '[':
            stack.append('[')
        elif ch == ']':
            if stack and stack[-1] == '[':
                stack.pop()

    repaired = raw_args

    # 如果截断在转义序列中间（\ 后面没字符），去掉不完整的转义符
    if escape:
        repaired = repaired[:-1]

    # 如果截断在字符串中间，先闭合字符串
    if in_string:
        repaired += '"'

    # 清理尾部不完整的语法元素
    stripped = repaired.rstrip()
    while stripped and stripped[-1] in (',', ':'):
        if stripped[-1] == ':':
            # 不完整的键值对，补 null
            stripped += 'null'
            break
        stripped = stripped[:-1].rstrip()
    repaired = stripped

    # 按照打开顺序的逆序闭合括号（保证嵌套正确）
    for opener in reversed(stack):
        repaired += ']' if opener == '[' else '}'

    try:
        result = json.loads(repaired)
        closers = ''.join(']' if o == '[' else '}' for o in reversed(stack))
        quote = '"' if in_string else ''
        print(f"[_try_parse_tool_args] ✅ 修复成功 (补了 {quote}{closers})")
        return result
    except json.JSONDecodeError as e:
        print(f"[_try_parse_tool_args] 修复后仍无法解析: {e}")
        print(f"[_try_parse_tool_args] 修复后末尾50字符: ...{repaired[-50:]}")
        return None


def run_subagent_sync(llm, task: str) -> str:
    """
    运行 SubAgent 完成文档生成任务（同步调用）

    SubAgent 架构（对标 VS Code Copilot SubAgent）：
    - 独立上下文窗口：不继承 MainAgent 的消息历史
    - 专用系统提示：只关注文档生成，不含搜索/查询等指令
    - 只接收 task 描述作为全部输入（MainAgent 应将搜索结果整合进 task）
    - 内部推理过程对 MainAgent 不可见
    - 只返回最终文档 JSON
    """
    print(f"[SubAgent] 启动，任务: {task[:100]}...")

    llm_with_tools = llm.bind_tools(SUBAGENT_TOOLS)

    # SubAgent 专用系统提示（不继承 MainAgent 的）
    system_prompt = get_subagent_prompt()

    # 注入当前时间
    from datetime import datetime
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    now = datetime.now()
    current_time = now.strftime("%Y年%m月%d日 %H:%M") + " " + weekdays[now.weekday()]

    # 构建干净的消息列表（独立上下文窗口）
    messages = [
        SystemMessage(content=system_prompt),
        SystemMessage(content=f"当前时间: {current_time}"),
        HumanMessage(content=task),
    ]

    # ReAct 循环
    max_steps = 10
    doc_result = None

    for step in range(max_steps):
        print(f"[SubAgent] Step {step + 1}")
        response = llm_with_tools.invoke(messages)

        # 修复 invalid_tool_calls（LLM 输出的 JSON 被截断时 LangChain 放到这里）
        invalid_tcs = getattr(response, "invalid_tool_calls", [])
        if invalid_tcs and not getattr(response, "tool_calls", []):
            for itc in invalid_tcs:
                tc_name = itc.get("name", "")
                raw_args = itc.get("args", "")
                tc_id = itc.get("id", "")
                print(f"[SubAgent] ⚠️ 修复 invalid_tool_call: {tc_name} (args长度={len(raw_args)})")
                parsed = _try_parse_tool_args(raw_args)
                if parsed is not None:
                    print(f"[SubAgent] ✅ 修复成功: {tc_name}")
                    response.tool_calls.append({
                        "name": tc_name,
                        "args": parsed,
                        "id": tc_id,
                        "type": "tool_call",
                    })
                    response.invalid_tool_calls = [
                        x for x in response.invalid_tool_calls if x.get("id") != tc_id
                    ]
                else:
                    print(f"[SubAgent] ❌ 无法修复: {tc_name}")

        messages.append(response)

        if not getattr(response, "tool_calls", []):
            break

        # 执行工具
        for tool_call in response.tool_calls:
            name = tool_call["name"]
            print(f"[SubAgent Tools] 执行: {name}")
            tool_fn = SUBAGENT_TOOL_MAP.get(name)
            if tool_fn:
                result = tool_fn.invoke(tool_call["args"])
                if isinstance(result, dict):
                    content = json.dumps(result, ensure_ascii=False)
                    if name == "generate_document":
                        doc_result = content
                else:
                    content = str(result)
                messages.append(ToolMessage(content=content, tool_call_id=tool_call["id"], name=name))
            else:
                messages.append(ToolMessage(
                    content=f"错误: 未知工具 {name}",
                    tool_call_id=tool_call["id"],
                    name=name,
                ))

    if doc_result:
        print(f"[SubAgent] ✅ 返回文档结果")
        return doc_result

    final = messages[-1]
    final_content = final.content if hasattr(final, "content") and final.content else ""
    print(f"[SubAgent] ✅ 返回文本结果 ({len(final_content)} 字符)")
    return final_content


# region Main Agent Graph


def build_main_graph(llm, llm_with_tools):
    """
    构建 MainAgent 主图

    流程：
    START -> agent -> (有 tool_calls?) -> tools -> agent -> ... -> END
                   -> (无 tool_calls) -> END

    tools_node 中遇到 run_subagent 时，启动独立的 SubAgent 执行。
    """
    graph = StateGraph(MessagesState)

    def agent_node(state: MessagesState) -> dict:
        """MainAgent 节点 - 决定下一步行动或直接回复"""
        print("[MainAgent] 开始处理")
        response = llm_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    def tools_node(state: MessagesState) -> dict:
        """工具执行节点 - 普通工具直接执行，run_subagent 启动独立 SubAgent"""
        last_message = state["messages"][-1]
        results = []

        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            print(f"[Main Tools] 执行工具: {tool_name}")

            if tool_name == "run_subagent":
                # 委派给 SubAgent（独立上下文窗口，不继承 MainAgent 消息）
                task = tool_call["args"].get("task", "")
                print(f"[Main Tools] 🤖 委派 SubAgent: {task[:80]}...")

                from langgraph.config import get_stream_writer
                writer = get_stream_writer()
                writer({"type": "status", "content": "🤖 正在委派子代理生成文档..."})

                content = run_subagent_sync(llm, task)
                results.append(ToolMessage(content=content, tool_call_id=tool_call["id"], name="run_subagent"))
                continue

            # 普通工具
            tool_fn = TOOL_MAP.get(tool_name)
            if tool_fn:
                result = tool_fn.invoke(tool_call["args"])
                if isinstance(result, dict):
                    content = json.dumps(result, ensure_ascii=False)
                elif isinstance(result, str):
                    content = result
                else:
                    content = str(result)
                results.append(ToolMessage(content=content, tool_call_id=tool_call["id"], name=tool_name))
            else:
                print(f"[Main Tools] ⚠️ 未知工具: {tool_name}")
                results.append(
                    ToolMessage(content=f"错误: 未知工具 {tool_name}", tool_call_id=tool_call["id"], name=tool_name)
                )

        return {"messages": results}

    def should_continue(state: MessagesState) -> str:
        """判断 MainAgent 是否还需要调用工具"""
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            print("[MainAgent Router] -> tools")
            return "tools"
        print("[MainAgent Router] -> END")
        return END

    graph.add_node("agent", agent_node)
    graph.add_node("tools", tools_node)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")

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
        llm_with_tools = llm.bind_tools(tools)
        # ask 模式不需要 SubAgent，用简单的单 Agent 图
        subagent_graph = None

        graph = StateGraph(MessagesState)

        def ask_agent_node(state: MessagesState) -> dict:
            print("[Agent] 开始处理")
            return {"messages": [llm_with_tools.invoke(state["messages"])]}

        def ask_tools_node(state: MessagesState) -> dict:
            last = state["messages"][-1]
            results = []
            for tc in last.tool_calls:
                tool_fn = TOOL_MAP.get(tc["name"])
                if tool_fn:
                    result = tool_fn.invoke(tc["args"])
                    content = json.dumps(result, ensure_ascii=False) if isinstance(result, dict) else str(result)
                    results.append(ToolMessage(content=content, tool_call_id=tc["id"], name=tc["name"]))
            return {"messages": results}

        def ask_router(state: MessagesState) -> str:
            last = state["messages"][-1]
            if hasattr(last, "tool_calls") and last.tool_calls:
                return "tools"
            return END

        graph.add_node("agent", ask_agent_node)
        graph.add_node("tools", ask_tools_node)
        graph.add_edge(START, "agent")
        graph.add_conditional_edges("agent", ask_router, {"tools": "tools", END: END})
        graph.add_edge("tools", "agent")
        app = graph.compile()
    else:
        # MainAgent 的工具集：不包含 generate_document（由 SubAgent 持有）
        print(f"[MainAgent] 已绑定 {[t.name for t in MAIN_TOOLS]}")
        print(f"[SubAgent] 工具集: {[t.name for t in SUBAGENT_TOOLS]}")
        llm_with_tools = llm.bind_tools(MAIN_TOOLS)

        # 构建主图（SubAgent 在 tools_node 中按需创建，独立上下文）
        app = build_main_graph(llm, llm_with_tools)

    try:
        # 构建初始消息列表
        messages = []

        # # 注入系统提示技能（拆分为多个 SystemMessage，便于维护和按模式裁剪）
        # for skill_prompt in get_agent_prompt_skills(mode=mode):
        #     messages.append(SystemMessage(content=skill_prompt))

        # 注入系统提示（从模块化 md 文件加载，合并为单条 SystemMessage 以兼容小模型）
        messages.append(SystemMessage(content=get_agent_prompt(mode=mode)))

        # 注入自定义提示（如果有）
        from app.services.llm_client import get_custom_prompt

        custom_prompt = get_custom_prompt()
        if custom_prompt:
            messages.append(SystemMessage(content=f"用户自定义指令: {custom_prompt}"))

        # 注入当前时间
        from datetime import datetime

        weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        now = datetime.now()
        current_time = now.strftime("%Y年%m月%d日 %H:%M") + " " + weekdays[now.weekday()]
        messages.append(SystemMessage(content=f"当前时间: {current_time}"))  # 注入当前时间，帮助模型做出与时俱进的回复

        # # 注入历史对话（最近 N 轮），让 Agent 了解上下文
        # if history:
        #     from langchain_core.messages import AIMessage

        #     MAX_HISTORY_PAIRS = 3  # 最多保留最近 3 轮对话
        #     # history 来自前端，格式: [{role: "user", content: "..."}, {role: "assistant", content: "..."}, ...]
        #     # 只取纯文本的 user/assistant 消息，跳过工具调用等
        #     hist_msgs = []
        #     for h in history:
        #         role = h.get("role", "")
        #         content = h.get("content", "")
        #         if not content or not isinstance(content, str):
        #             continue
        #         if role == "user":
        #             hist_msgs.append(HumanMessage(content=content))
        #         elif role == "assistant":
        #             hist_msgs.append(AIMessage(content=content))

        #     # 只保留最近 MAX_HISTORY_PAIRS 轮（每轮 = 1 user + 1 assistant）
        #     if len(hist_msgs) > MAX_HISTORY_PAIRS * 2:
        #         hist_msgs = hist_msgs[-(MAX_HISTORY_PAIRS * 2) :]

        #     if hist_msgs:
        #         messages.extend(hist_msgs)
        #         print(f"[Agent] 注入 {len(hist_msgs)} 条历史消息")

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
        generate_tool_result = False
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

                # 检测 LLM 开始调用 run_subagent
                if isinstance(msg, AIMessageChunk) and not generating_notified:
                    tool_call_chunks = getattr(msg, "tool_call_chunks", [])
                    for tc in tool_call_chunks:
                        if tc.get("name") in ("run_subagent", "generate_document"):
                            generating_notified = True
                            print("[Agent] 📝 检测到委派文档生成任务")
                            yield f"data: {json.dumps({'type': 'generate_document', 'content': '📝 正在准备生成文档'}, ensure_ascii=False)}\n\n"
                            break

                if isinstance(msg, ToolMessage):
                    # 根据工具名称决定是否转发给前端
                    tool_name = getattr(msg, "name", "")
                    has_tool_result = True

                    if tool_name == "read_document":
                        print(f"[Agent] ⏭️ 跳过 read_document 工具返回值")
                        continue

                    if tool_name == "run_subagent":
                        # SubAgent 返回的结果可能包含 generate_document 的文档 JSON
                        try:
                            doc_json = json.loads(content)
                            if "paragraphs" in doc_json:
                                generate_tool_result = True
                                print(f"[Agent] ✅ SubAgent 返回文档结果")
                                yield f"data: {json.dumps({'type': 'json', 'content': doc_json}, ensure_ascii=False)}\n\n"
                                continue
                        except json.JSONDecodeError:
                            pass
                        # 非文档 JSON，作为普通文本输出
                        if content:
                            yield f"data: {json.dumps({'type': 'text', 'content': content}, ensure_ascii=False)}\n\n"
                        continue

                    if tool_name == "generate_document":
                        # ask 模式下直接调用 generate_document 的情况
                        generate_tool_result = True
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

        # 处理"看到生成草稿但最终未真正调用 generate_document"的场景（仅打印日志，不推送给前端避免困惑）
        if generating_notified and not generate_tool_result:
            print("[Agent] ℹ️ 模型取消了文档生成，已直接输出文本结果")

        yield "data: [DONE]\n\n"

    except Exception as e:
        print(f"[Agent Error] {e}")
        traceback.print_exc()
        yield f"data: {json.dumps({'type': 'text', 'content': f'错误: {str(e)}'}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"