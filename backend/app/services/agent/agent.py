"""
文档处理 Agent - 使用 LangGraph ReAct 单一智能体 + 流式输出
重构后使用 build_graph + bind_tools，可直接访问 invalid_tool_calls 进行修复
"""

import asyncio
import concurrent.futures
import json
import os
import sys
import time
import traceback
from collections.abc import AsyncGenerator
from typing import Any

from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    HumanMessage,
    RemoveMessage,
    SystemMessage,
    ToolMessage,
)
from langgraph.graph import END, START, MessagesState, StateGraph

from app.services.llm_client import resolve_model, supports_thinking, init_chat_model_with_reasoning
from app.services.agent.prompts import get_core_prompts
from app.services.utils import normalize_tool_args, parse_tool_args_with_repair
from app.services.agent.tools import (
    TOOL_MAP,
    _current_chat_id,
    register_loop,
    is_stop_requested,
    get_base_tools_for_mode,
)
from app.services.agent.tools.callback import _current_model_name
from app.services.agent.tools.mcp_tools import load_mcp_tools, build_mcp_tools_prompt
from app.services.agent.skills import build_skills_prompt


def _get_env_int(name: str, default: int) -> int:
    """Read positive int env var with fallback."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(str(raw).strip())
        return value if value > 0 else default
    except Exception:
        return default


_AGENT_RECURSION_LIMIT = _get_env_int("WORDAGENT_AGENT_RECURSION_LIMIT", 25)


class ContextOverflowError(Exception):
    """
    上下文超限异常：携带压缩后的对话历史，
    通知调用方（chat.py）用压缩后的历史重试请求。
    """

    def __init__(self, message: str, compressed_history: list):
        super().__init__(message)
        self.compressed_history = compressed_history


# region LangSmith（可选，不影响正常运行）


def _try_init_langsmith():
    """尝试加载 .env 并初始化 LangSmith 环境变量，失败时静默跳过。"""
    try:
        from pathlib import Path
        from dotenv import load_dotenv

        candidates: list[Path] = []
        if getattr(sys, "frozen", False):
            candidates.append(Path(sys.executable).parent / ".env")
            meipass = getattr(sys, "_MEIPASS", None)
            if meipass:
                candidates.append(Path(meipass) / ".env")

        candidates.append(Path(__file__).resolve().parent.parent.parent.parent / ".env")
        candidates.append(Path.cwd() / ".env")

        seen: set[Path] = set()
        for env_path in candidates:
            try:
                resolved = env_path.resolve()
            except Exception:
                resolved = env_path
            if resolved in seen:
                continue
            seen.add(resolved)
            if resolved.exists():
                print(f"[LangSmith] 加载 .env: {resolved}")
                load_dotenv(resolved, override=False)

        api_key = os.environ.get("LANGSMITH_API_KEY")
        project = os.environ.get("LANGSMITH_PROJECT")

        if api_key and project:
            os.environ["LANGCHAIN_API_KEY"] = api_key
            os.environ["LANGCHAIN_PROJECT"] = project
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            print(f"[LangSmith] ✅ 已启用 tracing，project = {project}")
            return True
        else:
            print(f"[LangSmith] ⚠️ 未启用 - API_KEY: {'已设置' if api_key else '未设置'}, PROJECT: {project}")
    except Exception as e:
        print(f"[LangSmith] ⚠️ 初始化失败: {e}")
    return False


_langsmith_enabled = _try_init_langsmith()


# endregion


def _extract_text_content(content) -> str:
    """将 LLM 消息内容统一转换为纯文本，兼容 Claude 的结构化 content blocks。"""
    if content is None:
        return ""

    if isinstance(content, str):
        return content

    if isinstance(content, dict):
        text = content.get("text")
        if isinstance(text, str):
            return text
        fallback = content.get("content")
        return fallback if isinstance(fallback, str) else ""

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            item_text = _extract_text_content(item)
            if item_text:
                parts.append(item_text)
        return "".join(parts)

    return ""


def _extract_thinking_content(content) -> str:
    """提取 thinking/reasoning 内容，兼容 Claude 与 OpenAI 常见结构。"""
    if content is None:
        return ""

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            item_text = _extract_thinking_content(item)
            if item_text:
                parts.append(item_text)
        return "".join(parts)

    if not isinstance(content, dict):
        return ""

    block_type = str(content.get("type", "")).lower()

    if block_type == "thinking":
        for key in ("thinking", "text", "content"):
            val = content.get(key)
            if isinstance(val, str) and val:
                return val

    if block_type in {"reasoning", "reasoning_content", "summary_text"}:
        for key in ("reasoning", "text", "content"):
            val = content.get(key)
            if isinstance(val, str) and val:
                return val

        summary = content.get("summary")
        if summary is not None:
            summary_text = _extract_thinking_content(summary)
            if summary_text:
                return summary_text

    reasoning = content.get("reasoning")
    if isinstance(reasoning, str) and reasoning:
        return reasoning

    summary = content.get("summary")
    if summary is not None:
        return _extract_thinking_content(summary)

    return ""


def _is_transient_stream_error(exc: Exception) -> bool:
    """判断是否是可重试的流式网络错误。"""
    text = str(exc).lower()
    transient_signals = [
        "incomplete chunked read",
        "peer closed connection",
        "server disconnected",
        "connection reset",
        "read timeout",
        "remoteprotocolerror",
    ]
    return any(sig in text for sig in transient_signals)


def _is_context_overflow_error(exc: Exception) -> bool:
    """判断是否是上下文超限错误（413 等）。"""
    text = str(exc).lower()
    overflow_signals = ["413", "context_length", "too many tokens", "maximum context", "exceeds context", "token limit"]
    return any(sig in text for sig in overflow_signals)


# region LangGraph Agent（ReAct）


def build_graph(llm_with_tools, all_tools: list):
    """
    构建 LangGraph ReAct 工作流（单一智能体）

    流程：
    START -> agent -> (有 tool_calls) -> tools -> agent -> ... -> END
                   -> (有 invalid_tool_calls) -> repair -> agent -> ...
                   -> (无 tool_calls 且无 invalid_tool_calls) -> END

    Args:
        llm_with_tools: 绑定了工具的 LLM
        all_tools: 所有可用工具（包括 BASE_TOOLS + MCP_tools）

    关键改进：
    - repair 节点从 invalid_tool_calls 中提取原始 JSON 字符串进行修复并执行
    - 无需 LangChain 的 create_agent，避免 invalid_tool_calls 被吞掉
    """
    # 构建完整的工具查找表（BASE_TOOLS + MCP_tools）
    tool_map: dict[str, Any] = {t.name: t for t in all_tools}

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
        last_message = state["messages"][-1]
        results = []
        chat_id = _current_chat_id.get(None)

        for tool_call in last_message.tool_calls:
            if is_stop_requested(chat_id):
                print(f"[Tools] ⛔ 收到停止信号，终止后续工具执行 (session={chat_id})")
                break
            tool_name = tool_call["name"]
            print(f"[Tools] 执行工具: {tool_name}")

            tool_fn = tool_map.get(tool_name)
            if tool_fn:
                try:
                    # 用 normalize_tool_args 预处理参数，修复 JSON 字符串转义等问题
                    normalized_args = normalize_tool_args(tool_name, tool_call["args"])
                    result = tool_fn.invoke(normalized_args)
                    if isinstance(result, dict):
                        content = json.dumps(result, ensure_ascii=False)
                    elif isinstance(result, str):
                        content = result
                    else:
                        content = str(result)
                    results.append(ToolMessage(content=content, tool_call_id=tool_call["id"], name=tool_name))
                except Exception as e:
                    err = f"Error: tool {tool_name} failed: {e}"
                    print(f"[Tools] ❌ {err}")
                    results.append(ToolMessage(content=err, tool_call_id=tool_call["id"], name=tool_name))
            else:
                print(f"[Tools] ⚠️ 未知工具: {tool_name}")
                results.append(
                    ToolMessage(
                        content=f"Error: unknown tool {tool_name}", tool_call_id=tool_call["id"], name=tool_name
                    )
                )

        return {"messages": results}

    def repair_invalid_tool_call_node(state: MessagesState) -> dict:
        """
        修复 invalid_tool_calls 并直接执行。

        这是解决 escaped JSON 字符串问题的核心：
        - 模型生成的 document 参数可能是转义字符串 "{\"insertParaIndex\": ...}"
        - LangChain 的 parse_tool_call 会将这些放入 invalid_tool_calls
        - 我们在这里用 parse_tool_args_with_repair 尝试修复并执行
        """
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
                print(f"[Repair] ⚠️ 未知工具跳过: {tool_name}")
                continue

            raw_args = tc.get("args", "")
            error_msg = tc.get("error", "")
            print(f"[Repair] 尝试修复工具: {tool_name}")
            print(f"[Repair] 原始错误: {error_msg}")
            print(f"[Repair] 原始 args: {str(raw_args)[:200]}...")

            parsed_args = None
            for _ in range(3):
                if isinstance(raw_args, str):
                    raw_args_stripped = raw_args.strip()
                    try:
                        parsed = json.loads(raw_args_stripped)
                        raw_args = parsed
                    except json.JSONDecodeError:
                        pass
                    try:
                        import ast

                        parsed = ast.literal_eval(raw_args_stripped)
                        raw_args = parsed
                    except Exception:
                        pass

                if isinstance(raw_args, dict):
                    if "document" in raw_args and isinstance(raw_args.get("document"), dict):
                        raw_args = raw_args["document"]
                        continue
                    parsed_args = raw_args
                    break
                elif isinstance(raw_args, str):
                    continue
                else:
                    break

            if parsed_args is None:
                print(f"[Repair] ❌ 无法解析工具参数: {tool_name}")
                continue

            try:
                normalized_args = normalize_tool_args(tool_name, parsed_args)
            except Exception as norm_err:
                print(f"[Repair] ⚠️ normalize_tool_args 失败: {norm_err}，使用原始参数")
                normalized_args = parsed_args

            try:
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
                        "id": tc.get("id", "repaired"),
                        "type": "tool_call",
                    }
                )
                repaired_results.append(
                    ToolMessage(content=content, tool_call_id=tc.get("id", "repaired"), name=tool_name)
                )
                print(f"[Repair] ✅ 已修复并执行工具: {tool_name}")
            except Exception as e:
                print(f"[Repair] ❌ 工具执行失败: {tool_name}, error={e}")

        if repaired_tool_calls:
            print(f"[Repair] ✅ 成功修复 {len(repaired_tool_calls)} 个工具调用")
            return {
                "messages": [
                    RemoveMessage(id=last_message.id),
                    AIMessage(content="", tool_calls=repaired_tool_calls),
                    *repaired_results,
                ]
            }

        print("[Repair] ⚠️ 无法自动修复，提示模型重试")
        return {
            "messages": [
                RemoveMessage(id=last_message.id),
                SystemMessage(
                    content=(
                        "[RETRY_GENERATE] 你刚才的 tool call 参数无效（可能是 JSON 被转义或格式错误）。"
                        "请重试调用 generate_document，并确保："
                        "1) document 参数必须是 JSON 对象，不是字符串；"
                        "2) 不要使用 json.dumps() 或 escape quotes；"
                        "3) 段落样式使用 pStyle ID（如 pS_1），字符样式使用 rStyle ID（如 rS_2）；"
                        "4) 文本内容中如需引号，请使用中文引号或正确转义。"
                    )
                ),
            ]
        }

    # ---- 路由 ----

    def should_continue(state: MessagesState) -> str:
        """判断 Agent 是否还需要调用工具"""
        chat_id = _current_chat_id.get(None)
        if is_stop_requested(chat_id):
            print("[Router] -> END (用户停止)")
            return END

        last_message = state["messages"][-1]

        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            print(f"[Router] -> tools (有 {len(last_message.tool_calls)} 个有效工具调用)")
            return "tools"

        invalid_calls = getattr(last_message, "invalid_tool_calls", []) or []
        if invalid_calls:
            tool_names = [tc.get("name", "?") for tc in invalid_calls]
            print(f"[Router] ⚠️ 检测到无效工具调用: {tool_names}")
            for idx, tc in enumerate(invalid_calls, 1):
                print(
                    f"[Router] invalid_tool_call[{idx}] name={tc.get('name', '?')} "
                    f"error={tc.get('error', '?')} args={str(tc.get('args', ''))[:100]}"
                )
            print("[Router] -> repair")
            return "repair"

        print("[Router] -> END")
        return END

    # ---- 构建图 ----

    graph.add_node("agent", agent_node)
    graph.add_node("tools", tools_node)
    graph.add_node("repair", repair_invalid_tool_call_node)

    graph.add_edge(START, "agent")
    graph.add_conditional_edges(
        "agent",
        should_continue,
        {"tools": "tools", "repair": "repair", END: END},
    )
    graph.add_edge("tools", "agent")
    graph.add_edge("repair", "agent")

    return graph.compile()


# endregion


# region 主处理函数


async def process_writing_request_stream(
    message: str,
    document_range: list[dict] | None = None,
    document_meta: dict | None = None,
    history: list | None = None,
    model: str | None = None,
    provider: str | None = None,
    mode: str | None = None,
    chat_id: str | None = None,
    attached_files: list[dict] | None = None,
    enable_thinking: bool = True,
) -> AsyncGenerator[str, None]:
    """
    使用 LangGraph ReAct Agent 处理写作请求（流式输出）

    重构要点：
    - 使用 build_graph + llm.bind_tools 替代 create_agent
    - 保留 repair 节点处理 invalid_tool_calls
    - 保留所有原有功能（记忆、压缩、MCP、thinking）
    """
    mode = (mode or "agent").strip().lower()
    if mode == "plan":
        mode = "agent"
    elif mode not in {"agent", "ask"}:
        mode = "agent"

    print("[Agent] 开始处理请求")
    print(f"[Agent] 模式: {mode}")
    print(f"[Agent] 深度思考: {enable_thinking}")
    print("[Agent] 配置: recursion_limit =", _AGENT_RECURSION_LIMIT)

    model_name = resolve_model(model or "auto", provider or "")
    _thinking_enabled = enable_thinking and supports_thinking(model_name)
    llm = init_chat_model_with_reasoning(model_name, enable_thinking=_thinking_enabled)

    # ask 模式禁用 MCP；agent 模式按用户设置加载 MCP 动态工具
    mcp_clients = []
    if mode == "agent":
        mcp_tools, mcp_clients, mcp_failed_servers = await load_mcp_tools()
        for failed in mcp_failed_servers:
            server_name = str(failed.get("name") or "未命名服务器")
            error_text = str(failed.get("error") or "未知错误")
            if len(error_text) > 300:
                error_text = error_text[:300] + "..."
            yield f"data: {json.dumps({'type': 'status', 'content': f'⚠️ MCP 服务器 {server_name} 加载失败: {error_text}'}, ensure_ascii=False)}\n\n"
    else:
        mcp_tools = []
        mcp_failed_servers = []
    mcp_tool_names = {t.name for t in mcp_tools}
    tools = get_base_tools_for_mode(mode) + mcp_tools
    print(f"[Agent] 已绑定 {[t.name for t in tools]}")

    # 构建系统提示
    system_parts = list(get_core_prompts(mode=mode))

    # 注入长期记忆（来自 md 文件）
    from app.services.memory import build_long_term_memory_prompt

    long_term_prompt = build_long_term_memory_prompt()
    if long_term_prompt:
        system_parts.append(long_term_prompt)
        print("[Agent] 已注入长期记忆")

    if mode == "agent":
        mcp_prompt = build_mcp_tools_prompt(mcp_tools)
        if mcp_prompt:
            system_parts.append(mcp_prompt)
    skills_prompt = build_skills_prompt()
    if skills_prompt:
        system_parts.append(skills_prompt)
    from app.services.llm_client import get_custom_prompt

    custom_prompt = get_custom_prompt()
    if custom_prompt:
        system_parts.append(f"User custom instructions: {custom_prompt}")
    from datetime import datetime

    weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    now = datetime.now()
    current_time = now.strftime("%Y-%m-%d %H:%M") + " " + weekdays[now.weekday()]
    system_parts.append(f"Current time: {current_time}")
    system_prompt = "\n\n".join(system_parts)

    # 使用 bind_tools + build_graph（替代 create_agent）
    llm_with_tools = llm.bind_tools(tools)
    app = build_graph(llm_with_tools, tools)

    try:
        # 构建初始消息列表
        messages = []

        # 注入系统提示（单一 SystemMessage）
        messages.append(SystemMessage(content=system_prompt))

        # 注入短期记忆（仅保留最近 k 轮对话原文）
        from app.services.memory import build_short_term_messages

        short_term = build_short_term_messages(history)
        if short_term:
            messages.extend(short_term)
            print(f"[Agent] 注入 {len(short_term)} 条短期记忆")

        # 构建用户消息
        user_content = message
        if document_range:
            range_instructions = "\n".join(
                f"  - read_document(startParaIndex={r.get('startParaIndex', 0)}, endParaIndex={r.get('endParaIndex', -1)})"
                for r in document_range
            )
            if mode == "ask":
                user_content = (
                    f"User request: {message}\n\n"
                    f"⚠️ First call read_document for the following ranges (mandatory, do not skip):\n{range_instructions}\n"
                    f"After reading the document content, answer the question with analysis and suggestions. "
                    f"If professional review feedback is needed, call run_sub_agent(agent_type='reviewer')."
                )
            else:
                user_content = (
                    f"User request: {message}\n\n"
                    f"⚠️ First call read_document for the following ranges (mandatory, do not skip):\n{range_instructions}\n"
                    f"After reading the document content, continue based on the user request. "
                    f"For writing/modification, prioritize direct calls to generate_document/delete_document. "
                    f"If professional review feedback is needed, call run_sub_agent(agent_type='reviewer')."
                )
            print(f"[Agent] 文档范围: {document_range}")

        # 注入文档全局元信息
        if document_meta:
            meta_text = json.dumps(document_meta, ensure_ascii=False)
            user_content += (
                "\n\n[Document Global Metadata]"
                "\nThe following fields come from frontend document state and are not body content."
                f"\n{meta_text}"
                "\nUse these metadata fields in task analysis (e.g., totalParas, documentName, parsedAt)."
            )
            print(
                "[Agent] 文档元信息:",
                {
                    "documentName": document_meta.get("documentName", ""),
                    "totalParas": document_meta.get("totalParas", 0),
                    "parsedAt": document_meta.get("parsedAt", ""),
                },
            )

        # 处理附件
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
                    text = read_text_file(file_id, filename)
                    if text:
                        text_file_parts.append(f"\n--- 附件: {filename} ---\n{text}")
                        print(f"[Agent] 📄 附件文本: {filename} ({len(text)} chars)")

        if text_file_parts:
            user_content += "\n" + "\n".join(text_file_parts)

        # 构建 HumanMessage
        if image_content_parts:
            human_content = [{"type": "text", "text": user_content}] + image_content_parts
            messages.append(HumanMessage(content=human_content))
        else:
            messages.append(HumanMessage(content=user_content))

        print(f"[Agent] 消息数量: {len(messages)}")

        # 获取事件循环
        loop = asyncio.get_running_loop()
        if chat_id:
            register_loop(chat_id, loop)

        # 队列用于线程间传递流式数据
        queue: asyncio.Queue = asyncio.Queue()
        has_tool_result = False
        _collected_text_parts: list[str] = []
        _has_streamed_text_chunks = False
        _agent_turn_count = 0
        _last_input_tokens = 0
        _conversation_history: list = list(messages)

        # LangSmith tracing
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

                import uuid as _uuid

                _thread_id = str(_uuid.uuid4())
                _config = {
                    "configurable": {"thread_id": _thread_id},
                    "recursion_limit": _AGENT_RECURSION_LIMIT,
                }
                if langsmith_config:
                    _config.update(langsmith_config)

                stream_kwargs = {
                    "input": {"messages": messages},
                    "stream_mode": ["messages", "custom"],
                    "config": _config,
                }

                max_attempts = 2
                for attempt in range(1, max_attempts + 1):
                    has_any_stream_item = False
                    try:
                        response = app.stream(**stream_kwargs)

                        for stream_item in response:
                            has_any_stream_item = True
                            if chat_id and is_stop_requested(chat_id):
                                print(f"[Agent] ⛔ 检测到停止信号，结束流式处理 (session={chat_id})")
                                break
                            asyncio.run_coroutine_threadsafe(queue.put(stream_item), loop)

                        asyncio.run_coroutine_threadsafe(queue.put(None), loop)
                        return
                    except Exception as e:
                        if _is_context_overflow_error(e):
                            print(f"[Agent] ⚠️ 上下文超限错误（{e}），触发被动重量重压缩")
                            asyncio.run_coroutine_threadsafe(queue.put(("context_overflow", str(e))), loop)
                            raise
                        if attempt < max_attempts and (not has_any_stream_item) and _is_transient_stream_error(e):
                            print(f"[Agent] ⚠️ 流式连接异常（第 {attempt} 次）: {e}，准备重试")
                            time.sleep(0.5)
                            continue
                        raise
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

            # 上下文超限被动重压缩
            if isinstance(stream_item, tuple) and stream_item[0] == "context_overflow":
                print(f"[Agent] ⚠️ 收到上下文超限信号，触发被动重量重压缩")
                from app.services.memory import compress_conversation_history_if_needed, _estimate_messages_tokens

                current_tokens = _estimate_messages_tokens(_conversation_history)
                compressed, meta = compress_conversation_history_if_needed(
                    _conversation_history,
                    llm=llm,
                    query=message,
                    history=history,
                    compact_level="heavy",
                )
                heavy_meta = meta.get("heavy_compact", {})
                if heavy_meta.get("heavy_compact_triggered"):
                    before = heavy_meta.get("before_tokens", current_tokens)
                    after = heavy_meta.get("after_tokens", 0)
                    print(f"[Agent] 🗜️ 被动重量重压缩完成: {before} -> {after} tokens")
                    updated_history = []
                    for m in compressed:
                        role = {"HumanMessage": "user", "AIMessage": "assistant", "SystemMessage": "system"}.get(
                            type(m).__name__, "assistant"
                        )
                        content_val = getattr(m, "content", "")
                        if hasattr(content_val, "__iter__") and not isinstance(content_val, str):
                            text_content = "".join(
                                part.get("text", "")
                                if isinstance(part, dict)
                                else (part if isinstance(part, str) else "")
                                for part in content_val
                            )
                            content_val = text_content
                        if isinstance(m, (HumanMessage, AIMessage, SystemMessage)):
                            updated_history.append({"role": role, "content": str(content_val)})
                    raise ContextOverflowError("上下文超限，已触发重量重压缩", updated_history)
                else:
                    print("[Agent] ⚠️ 被动重量重压缩失败，无法生成摘要")
                    raise Exception("上下文超限但重量重压缩失败，请手动减少对话历史")

            if not isinstance(stream_item, tuple):
                continue

            input_type, chunk = stream_item

            if input_type == "messages":
                if not chunk or len(chunk) == 0:
                    continue
                msg = chunk[0]
                content = msg.content

                # reasoning_content 透传（OpenAI/DeepSeek）
                if isinstance(msg, AIMessageChunk):
                    reasoning_content = getattr(msg, "additional_kwargs", {}).get("reasoning_content")
                    if reasoning_content:
                        yield f"data: {json.dumps({'type': 'thinking', 'content': reasoning_content}, ensure_ascii=False)}\n\n"

                # AIMessage：完整响应，追踪历史和 token
                if isinstance(msg, AIMessage):
                    _conversation_history.append(msg)
                    usage = getattr(msg, "usage_metadata", None)
                    if isinstance(usage, dict) and "input_tokens" in usage and usage.get("input_tokens", 0) > 0:
                        _last_input_tokens = int(usage.get("input_tokens", 0))
                        from app.services.memory import MAX_CONTEXT_TOKENS

                        tokens_k = _last_input_tokens / 1000
                        max_tokens_k = MAX_CONTEXT_TOKENS / 1000
                        print(f"[Agent] 当前上下文: {tokens_k:.1f}k tokens")
                        yield f"data: {json.dumps({'type': 'token_stats', 'current_tokens': _last_input_tokens, 'max_tokens': MAX_CONTEXT_TOKENS}, ensure_ascii=False)}\n\n"

                # AIMessageChunk：流式中间块，收集文本
                if isinstance(msg, AIMessageChunk):
                    normalized = _extract_text_content(msg.content)
                    if normalized:
                        _collected_text_parts.append(normalized)
                        # 关键：某些模型在流式场景只产出 AIMessageChunk 而不会产出最终 AIMessage。
                        # 如果不在这里转发 text，前端可能只能看到 thinking，正式输出为空。
                        _has_streamed_text_chunks = True
                        yield f"data: {json.dumps({'type': 'text', 'content': normalized}, ensure_ascii=False)}\n\n"

                # ToolMessage：工具执行结果
                if isinstance(msg, ToolMessage):
                    _conversation_history.append(msg)
                    _agent_turn_count += 1
                    tool_name = getattr(msg, "name", "")
                    has_tool_result = True

                    if tool_name == "read_document":
                        print(f"[Agent] ⏭️ 跳过 read_document 工具返回值")
                        continue

                    if tool_name == "run_sub_agent":
                        print(f"[Agent] ⏭️ 跳过 run_sub_agent 工具返回值")
                        if isinstance(content, str) and content.startswith("Sub-agent execution failed"):
                            yield f"data: {json.dumps({'type': 'status', 'content': content}, ensure_ascii=False)}\n\n"
                        elif isinstance(content, str) and content:
                            _collected_text_parts.append(content)
                        continue

                    if tool_name == "generate_document":
                        doc_json = None
                        try:
                            if isinstance(content, dict):
                                doc_json = content
                            elif isinstance(content, str):
                                try:
                                    doc_json = json.loads(content)
                                except json.JSONDecodeError:
                                    import ast

                                    doc_json = ast.literal_eval(content)
                        except Exception:
                            pass

                        if isinstance(doc_json, dict) and "paragraphs" in doc_json:
                            yield f"data: {json.dumps({'type': 'json', 'content': doc_json}, ensure_ascii=False)}\n\n"
                            continue

                    # MCP 工具日志
                    if tool_name in mcp_tool_names:
                        print(
                            f"[Agent] MCP 工具 {tool_name} 返回类型: {type(content).__name__}, 预览: {str(content)[:200]}"
                        )
                    continue

                # AIMessage：处理 content blocks（thinking/reasoning）
                if isinstance(msg, AIMessage):
                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict):
                                block_type = str(block.get("type", "")).lower()

                                if block_type in {"thinking", "reasoning", "reasoning_content", "summary_text"}:
                                    thinking_text = _extract_thinking_content(block)
                                    if thinking_text:
                                        yield f"data: {json.dumps({'type': 'thinking', 'content': thinking_text}, ensure_ascii=False)}\n\n"
                                    continue

                                if block_type in {"text", "output_text"}:
                                    text = block.get("text", "") or block.get("content", "")
                                    if text:
                                        _collected_text_parts.append(text)
                                        if not _has_streamed_text_chunks:
                                            yield f"data: {json.dumps({'type': 'text', 'content': text}, ensure_ascii=False)}\n\n"
                        continue

                    # 普通文本
                    normalized_text = _extract_text_content(content)
                    if normalized_text:
                        _collected_text_parts.append(normalized_text)
                        if not _has_streamed_text_chunks:
                            yield f"data: {json.dumps({'type': 'text', 'content': normalized_text}, ensure_ascii=False)}\n\n"

            elif input_type == "custom":
                # stream_writer 输出（工具状态消息）
                print(f"[Agent] 自定义输出: {chunk}")
                if chunk:
                    if isinstance(chunk, dict):
                        yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                    else:
                        yield f"data: {json.dumps({'type': 'status', 'content': str(chunk)}, ensure_ascii=False)}\n\n"

        # 警告
        if mode == "agent" and not has_tool_result and document_range:
            yield f"data: {json.dumps({'type': 'status', 'content': '⚠️ 没有检测到调用工具，模型可能不支持'}, ensure_ascii=False)}\n\n"

        yield "data: [DONE]\n\n"

    except Exception as e:
        print(f"[Agent Error] {e}")
        traceback.print_exc()
        yield f"data: {json.dumps({'type': 'text', 'content': f'Error: {str(e)}'}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
