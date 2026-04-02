"""
文档处理 Agent - 使用 LangGraph ReAct 单一智能体 + 流式输出
"""

import asyncio
import concurrent.futures
import json
import os
import traceback
from collections.abc import AsyncGenerator


# region LangSmith（可选，不影响正常运行）


def _try_init_langsmith():
    """尝试加载 .env 并初始化 LangSmith 环境变量，失败时静默跳过。"""
    try:
        from pathlib import Path
        from dotenv import load_dotenv

        env_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"
        if env_path.exists():
            load_dotenv(env_path, override=False)
        # 只有同时存在 key 和 tracing=true 时才视为可用
        if os.environ.get("LANGSMITH_TRACING", "").lower() == "true" and os.environ.get("LANGSMITH_API_KEY"):
            print("[LangSmith] ✅ 已启用 tracing，project =", os.environ.get("LANGSMITH_PROJECT", "default"))
            return True
    except Exception:
        pass
    return False


_langsmith_enabled = _try_init_langsmith()

from langchain_core.messages import AIMessage, HumanMessage, RemoveMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, MessagesState, StateGraph

from app.services.llm_client import create_llm, resolve_model
from app.services.agent.prompts import get_core_prompts
from app.services.utils import normalize_tool_args, parse_tool_args_with_repair
from app.services.agent.tools import (
    BASE_TOOLS,
    _current_chat_id,
    register_loop,
    is_stop_requested,
)
from app.services.agent.tools.callback import _current_model_name
from app.services.agent.tools.mcp_tools import load_mcp_tools, build_mcp_tools_prompt


# region LangGraph Agent（ReAct）


def build_graph(llm_with_tools, tool_map: dict, mcp_tool_names: set[str] | None = None):
    """
    构建 LangGraph ReAct 工作流（单一智能体）

    流程：
    START -> agent -> (有 tool_calls?) -> tools -> agent -> ... -> END
                   -> (无 tool_calls) -> END

    agent 自动循环调用工具，直到不再需要工具为止。
    """
    tool_names_str = " / ".join(tool_map.keys())
    _mcp_names = mcp_tool_names or set()
    graph = StateGraph(MessagesState)

    # ---- 节点 ----

    def agent_node(state: MessagesState) -> dict:
        """单一 Agent 节点 - 决定下一步行动或直接回复"""
        chat_id = _current_chat_id.get(None)
        if is_stop_requested(chat_id):
            print(f"[Agent] ⛔ 收到停止信号，终止 Agent 节点 (session={chat_id})")
            return {"messages": []}
        print("[Agent] 开始处理")
        response = llm_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    def tools_node(state: MessagesState) -> dict:
        """工具执行节点 - 执行 Agent 请求的所有工具"""
        from langgraph.config import get_stream_writer as _get_sw

        last_message = state["messages"][-1]
        results = []
        chat_id = _current_chat_id.get(None)
        writer = _get_sw()

        for tool_call in last_message.tool_calls:
            if is_stop_requested(chat_id):
                print(f"[Tools] ⛔ 收到停止信号，终止后续工具执行 (session={chat_id})")
                break
            tool_name = tool_call["name"]
            print(f"[Tools] 执行工具: {tool_name}")

            # MCP 工具调用时输出状态到前端
            if tool_name in _mcp_names:
                args_preview = json.dumps(tool_call.get("args", {}), ensure_ascii=False)
                if len(args_preview) > 100:
                    args_preview = args_preview[:100] + "..."
                writer({"type": "status", "content": f"🔧 调用 MCP 工具: {tool_name}({args_preview})"})

            tool_fn = tool_map.get(tool_name)
            if tool_fn:
                try:
                    tool_args = normalize_tool_args(tool_name, tool_call.get("args", {}))
                    result = tool_fn.invoke(tool_args)
                    # 标准化结果为字符串
                    if isinstance(result, dict):
                        content = json.dumps(result, ensure_ascii=False)
                    elif isinstance(result, str):
                        content = result
                    else:
                        content = str(result)

                    results.append(ToolMessage(content=content, tool_call_id=tool_call["id"], name=tool_name))
                except Exception as e:
                    err = (
                        f"错误: 工具 {tool_name} 调用失败: {e}。"
                        "请按工具 schema 重新构造参数。"
                    )
                    print(f"[Tools] ❌ {err}")
                    results.append(ToolMessage(content=err, tool_call_id=tool_call["id"], name=tool_name))
            else:
                print(f"[Tools] ⚠️ 未知工具: {tool_name}")
                results.append(
                    ToolMessage(content=f"错误: 未知工具 {tool_name}", tool_call_id=tool_call["id"], name=tool_name)
                )

        return {"messages": results}

    def retry_node(state: MessagesState) -> dict:
        """当模型中途放弃 tool call 时，移除失败的消息并提示重试"""
        last_message = state["messages"][-1]
        invalid_calls = getattr(last_message, "invalid_tool_calls", [])
        tool_names = [tc.get("name", "?") for tc in invalid_calls] if invalid_calls else []
        print(f"[Retry] 移除失败的消息 (invalid tools: {tool_names})，添加重试提示")
        return {
            "messages": [
                RemoveMessage(id=last_message.id),
                SystemMessage(
                    content="[RETRY_TOOL_CALL] 你刚才的工具调用无效（可能是 JSON 不完整或被截断）。"
                    f"请基于当前可用工具重试一次：{tool_names_str}。"
                    "文档改写优先由你直接调用 generate_document/delete_document 完成；仅在简化场景可调用 run_sub_agent(agent_type='simplifier')。"
                ),
            ]
        }

    def repair_invalid_tool_call_node(state: MessagesState) -> dict:
        """尝试修复 invalid_tool_calls 并直接执行，减少二次生成失败概率。"""
        last_message = state["messages"][-1]
        invalid_calls = getattr(last_message, "invalid_tool_calls", []) or []
        chat_id = _current_chat_id.get(None)
        repaired_tool_calls = []
        repaired_results = []

        for tc in invalid_calls:
            if is_stop_requested(chat_id):
                print(f"[Repair] ⛔ 收到停止信号，终止修复执行 (session={chat_id})")
                break

            tool_name = tc.get("name", "")
            tool_fn = tool_map.get(tool_name)
            if not tool_fn:
                continue

            parsed_args = parse_tool_args_with_repair(tc.get("args", {}))
            if parsed_args is None:
                print(f"[Repair] ❌ 无法修复工具参数: {tool_name}")
                continue

            try:
                normalized_args = normalize_tool_args(tool_name, parsed_args)
                result = tool_fn.invoke(normalized_args)
                if isinstance(result, dict):
                    content = json.dumps(result, ensure_ascii=False)
                elif isinstance(result, str):
                    content = result
                else:
                    content = str(result)

                repaired_tool_calls.append(
                    {
                        "name": tool_name,
                        "args": normalized_args,
                        "id": tc.get("id", "repaired_invalid_tool_call"),
                        "type": "tool_call",
                    }
                )
                repaired_results.append(
                    ToolMessage(
                        content=content,
                        tool_call_id=tc.get("id", "repaired_invalid_tool_call"),
                        name=tool_name,
                    )
                )
                print(f"[Repair] ✅ 已修复并执行工具: {tool_name}")
            except Exception as e:
                print(f"[Repair] ❌ 工具执行失败: {tool_name}, error={e}")

        if repaired_results:
            print("[Repair] ✅ 已重建合法 tool_calls，继续 Agent")
            return {
                "messages": [
                    RemoveMessage(id=last_message.id),
                    AIMessage(content="", tool_calls=repaired_tool_calls),
                    *repaired_results,
                ]
            }

        # 无法修复时，回退到一次重试指令
        print("[Repair] -> retry (无法自动修复参数)")
        return {
            "messages": [
                RemoveMessage(id=last_message.id),
                SystemMessage(
                    content="[RETRY_TOOL_CALL] 你刚才的 tool call 参数不是合法 JSON。"
                    "请仅重试一次，并确保参数完整合法。"
                    f"可用工具：{tool_names_str}。"
                ),
            ]
        }

    # ---- 路由 ----

    # 最大工具调用轮次（agent -> tools -> agent 算一轮），防止无限循环
    MAX_TOOL_ROUNDS = 20

    def should_continue(state: MessagesState) -> str:
        """判断 Agent 是否还需要调用工具"""
        chat_id = _current_chat_id.get(None)
        if is_stop_requested(chat_id):
            print(f"[Router] -> END (用户停止, session={chat_id})")
            return END

        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            # 统计已完成的工具调用轮次（ToolMessage 的数量近似于轮次）
            tool_rounds = sum(1 for m in state["messages"] if isinstance(m, ToolMessage))
            if tool_rounds >= MAX_TOOL_ROUNDS:
                print(f"[Router] -> END (已达到最大工具调用轮次 {MAX_TOOL_ROUNDS})")
                return END
            print(f"[Router] -> tools (第 {tool_rounds + 1} 轮)")
            return "tools"

        # 优先尝试修复 invalid_tool_calls（模型生成了非法 JSON 参数）
        invalid_calls = getattr(last_message, "invalid_tool_calls", [])
        if invalid_calls:
            print(f"[Router] ⚠️ 检测到无效的工具调用: {[tc.get('name', '?') for tc in invalid_calls]}")
            for idx, tc in enumerate(invalid_calls, 1):
                print(
                    "[Router] invalid_tool_call[{idx}] name={name} id={id} error={error} args={args}".format(
                        idx=idx,
                        name=tc.get("name", "?"),
                        id=tc.get("id", "?"),
                        error=tc.get("error", "?"),
                        args=tc.get("args", ""),
                    )
                )
            print("[Router] -> repair")
            return "repair"

        # 检测中途放弃的工具调用，自动重试一次
        should_retry = False

        # 信号2: finish_reason 为 length（输出被截断）
        metadata = getattr(last_message, "response_metadata", {})
        finish_reason = metadata.get("finish_reason")
        if finish_reason:
            print(f"[Router] finish_reason={finish_reason}")
        if finish_reason == "length":
            print("[Router] ⚠️ 模型输出被截断 (finish_reason=length)")
            should_retry = True

        if should_retry:
            # 检查是否已经重试过（防止无限循环）
            has_retried = any(
                isinstance(m, SystemMessage) and "[RETRY_TOOL_CALL]" in m.content for m in state["messages"]
            )
            if not has_retried:
                print("[Router] -> retry")
                return "retry"
            else:
                print("[Router] -> END (已重试过，不再重试)")

        print("[Router] -> END")
        return END

    # ---- 构建图 ----

    graph.add_node("agent", agent_node)
    graph.add_node("tools", tools_node)
    graph.add_node("retry", retry_node)
    graph.add_node("repair", repair_invalid_tool_call_node)

    graph.add_edge(START, "agent")
    graph.add_conditional_edges(
        "agent",
        should_continue,
        {"tools": "tools", "retry": "retry", "repair": "repair", END: END},
    )
    graph.add_edge("tools", "agent")  # 工具执行完毕，始终回到 Agent
    graph.add_edge("retry", "agent")  # 重试后回到 Agent 重新生成
    graph.add_edge("repair", "agent")  # 修复执行后回到 Agent 收尾

    return graph.compile()


# region 主处理函数


async def process_writing_request_stream(
    message: str,
    document_range: list[dict] | None = None,
    document_meta: dict | None = None,
    history: list | None = None,
    model: str | None = None,
    mode: str | None = None,
    chat_id: str | None = None,
    attached_files: list[dict] | None = None,
) -> AsyncGenerator[str, None]:
    """
    使用 LangGraph ReAct Agent 处理写作请求（流式输出）

    Args:
        message: 用户消息
        document_range: 文档范围列表 [{startParaIndex: int, endParaIndex: int}, ...]
        document_meta: 文档全局元信息（如 totalParas/documentName/parsedAt 等）
        history: 历史消息
        model: 用户选择的模型
        mode: 对话模式（agent/plan）
        chat_id: WebSocket 会话 ID（用于工具回调）
        attached_files: 附件列表 [{file_id, filename, content_type, is_image}, ...]

    Yields:
        SSE 格式的流式输出
    """
    print("[Agent] 开始处理请求")
    print(f"[Agent] 模式: {mode}")

    model_name = resolve_model(model or "auto")
    llm = create_llm(model_name)

    # 加载 MCP 动态工具（从用户设置）
    mcp_tools, mcp_client = await load_mcp_tools()
    mcp_tool_names = {t.name for t in mcp_tools}
    tools = list(BASE_TOOLS) + mcp_tools
    tool_map = {t.name: t for t in tools}
    print(f"[Agent] 已绑定 {[t.name for t in tools]}")

    llm_with_tools = llm.bind_tools(tools)
    app = build_graph(llm_with_tools, tool_map, mcp_tool_names)

    try:
        # 构建初始消息列表
        messages = []

        # 注入核心技能（身份、风格、工具策略、子智能体策略等 — 始终加载）
        for core_prompt in get_core_prompts(mode=mode):
            messages.append(SystemMessage(content=core_prompt))

        # 注入 MCP 工具提示（让模型知道有哪些额外工具可用）
        mcp_prompt = build_mcp_tools_prompt(mcp_tools)
        if mcp_prompt:
            messages.append(SystemMessage(content=mcp_prompt))

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

        # 注入三层记忆（长期 RAG → 摘要 → 短期 k=5 轮）
        from app.services.memory import build_memory_messages

        memory_msgs = build_memory_messages(
            history=history,
            current_message=message,
            llm=llm,
            session_id=chat_id,
        )
        if memory_msgs:
            messages.extend(memory_msgs)
            print(f"[Agent] 注入 {len(memory_msgs)} 条记忆消息")

        # 构建用户消息
        user_content = message
        if document_range:
            # 有文档范围时，指示 agent 调用 read_document 读取这些范围
            range_instructions = "\n".join(
                f"  - read_document(startParaIndex={r.get('startParaIndex', 0)}, endParaIndex={r.get('endParaIndex', -1)})"
                for r in document_range
            )
            user_content = (
                f"用户要求：{message}\n\n"
                f"⚠️ 请先调用 read_document 工具读取以下文档范围（必须调用，不可跳过）：\n{range_instructions}\n"
                f"读取到文档内容后，根据用户要求继续处理。"
                f"文档修改与写作优先由你直接调用 generate_document/delete_document 完成。"
                f"仅在明确需要文本简化时，才调用 run_sub_agent(agent_type='simplifier')。"
            )
            print(f"[Agent] 文档范围: {document_range}")

        # 注入文档全局元信息（随用户提问发送）
        if document_meta:
            meta_text = json.dumps(document_meta, ensure_ascii=False)
            user_content += (
                "\n\n[文档全局元信息]"
                "\n以下属性来自前端当前文档状态，不是正文内容。"
                f"\n{meta_text}"
                "\n请在分析任务时结合这些元信息（例如 totalParas、documentName、parsedAt 等）。"
            )
            print(
                "[Agent] 文档元信息:",
                {
                    "documentName": document_meta.get("documentName", ""),
                    "totalParas": document_meta.get("totalParas", 0),
                    "parsedAt": document_meta.get("parsedAt", ""),
                },
            )

        # 处理附件：图片走多模态，文本类文件注入为上下文
        image_content_parts = []
        text_file_parts = []
        if attached_files:
            from app.api.routes.files import read_file_as_base64, read_text_file

            for f in attached_files:
                file_id = f.get("file_id", "")
                filename = f.get("filename", "")
                content_type = f.get("content_type", "")
                is_image = f.get("is_image", False)

                if is_image:
                    # 图片转 base64 作为多模态内容
                    b64 = read_file_as_base64(file_id)
                    if b64:
                        image_content_parts.append(
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:{content_type};base64,{b64}"},
                            }
                        )
                        print(f"[Agent] 🖼️ 附件图片: {filename}")
                else:
                    # 非图片文件，提取文本内容
                    text = read_text_file(file_id, filename)
                    if text:
                        text_file_parts.append(f"\n--- 附件: {filename} ---\n{text}")
                        print(f"[Agent] 📄 附件文本: {filename} ({len(text)} chars)")

        # 将文本附件内容追加到用户消息
        if text_file_parts:
            user_content += "\n" + "\n".join(text_file_parts)

        # 构建 HumanMessage：如果有图片则使用多模态格式，否则纯文本
        if image_content_parts:
            human_content = [{"type": "text", "text": user_content}] + image_content_parts
            messages.append(HumanMessage(content=human_content))
        else:
            messages.append(HumanMessage(content=user_content))

        print(f"[Agent] 消息数量: {len(messages)}")

        # 获取事件循环，注册供 tool 使用
        loop = asyncio.get_running_loop()
        if chat_id:
            register_loop(chat_id, loop)

        # 队列用于线程间传递流式数据
        queue: asyncio.Queue = asyncio.Queue()
        has_tool_result = False
        _collected_text_parts: list[str] = []  # 收集 AI 回复文本，用于存入长期记忆
        # 构建 LangSmith tracing config（可选）
        langsmith_config = None
        if _langsmith_enabled:
            try:
                run_name = f"agent:{model_name}"
                langsmith_config = {
                    "run_name": run_name,
                    "tags": ["agent", model_name, mode or "agent"],
                    "metadata": {
                        "model": model_name,
                        "mode": mode or "agent",
                        "has_document_range": bool(document_range),
                        "has_document_meta": bool(document_meta),
                        "chat_id": chat_id or "",
                    },
                }
            except Exception:
                langsmith_config = None

        def run_stream():
            """在独立线程中运行同步的 LangGraph stream"""
            try:
                if chat_id:
                    _current_chat_id.set(chat_id)
                _current_model_name.set(model_name)

                stream_kwargs = {
                    "input": {"messages": messages},
                    "stream_mode": ["messages", "custom"],
                }
                if langsmith_config:
                    stream_kwargs["config"] = langsmith_config

                response = app.stream(**stream_kwargs)

                for stream_item in response:
                    if chat_id and is_stop_requested(chat_id):
                        print(f"[Agent] ⛔ 检测到停止信号，结束流式处理 (session={chat_id})")
                        break
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

                if isinstance(msg, ToolMessage):
                    # 根据工具名称决定是否转发给前端
                    tool_name = getattr(msg, "name", "")
                    has_tool_result = True

                    if tool_name == "read_document":
                        # read_document 结果是中间数据，不发给前端
                        print(f"[Agent] ⏭️ 跳过 read_document 工具返回值")
                        continue

                    if tool_name == "run_sub_agent":
                        # run_sub_agent 结果是子智能体返回的摘要，不直接转发
                        # （子智能体状态与文档 JSON 已通过 stream_writer 转发）
                        print(f"[Agent] ⏭️ 跳过 run_sub_agent 工具返回值")
                        # 失败信息主动透传，避免前端无反馈
                        if isinstance(content, str) and content.startswith("子智能体执行失败"):
                            yield f"data: {json.dumps({'type': 'status', 'content': content}, ensure_ascii=False)}\n\n"
                        elif isinstance(content, str) and content:
                            _collected_text_parts.append(content)
                        continue

                    if tool_name == "generate_document":
                        # 主 Agent 直接生成文档时，透传 JSON 给前端
                        try:
                            doc_json = json.loads(content)
                            if isinstance(doc_json, dict) and "paragraphs" in doc_json:
                                yield f"data: {json.dumps({'type': 'json', 'content': doc_json}, ensure_ascii=False)}\n\n"
                                continue
                        except (json.JSONDecodeError, TypeError):
                            pass

                    # 其他工具的结果，跳过
                    continue

                # 普通文本输出（Agent 的回复）
                if content:
                    _collected_text_parts.append(content)
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
        if not has_tool_result and document_range:
            yield f"data: {json.dumps({'type': 'status', 'content': '⚠️ 没有检测到调用工具，模型可能不支持'}, ensure_ascii=False)}\n\n"

        # 将本轮对话存入长期记忆
        assistant_text = "".join(_collected_text_parts)
        if assistant_text or has_tool_result:
            try:
                from app.services.memory import store_conversation_to_long_term

                store_conversation_to_long_term(
                    session_id=chat_id or "",
                    user_message=message,
                    assistant_message=assistant_text or "[已执行工具]",
                    model=model,
                    mode=mode,
                )
            except Exception as mem_err:
                print(f"[Agent] ⚠️ 存入长期记忆失败: {mem_err}")

        yield "data: [DONE]\n\n"

    except Exception as e:
        print(f"[Agent Error] {e}")
        traceback.print_exc()
        yield f"data: {json.dumps({'type': 'text', 'content': f'错误: {str(e)}'}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
