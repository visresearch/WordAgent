"""
文档处理 Agent - 使用 LangGraph ReAct 单一智能体 + 流式输出
"""

import asyncio
import concurrent.futures
import json
import os
import sys
import time
import traceback
from collections.abc import AsyncGenerator


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
                load_dotenv(resolved, override=False)

        # 只有同时存在 key 和 tracing=true 时才视为可用
        if os.environ.get("LANGSMITH_TRACING", "").lower() == "true" and os.environ.get("LANGSMITH_API_KEY"):
            print("[LangSmith] ✅ 已启用 tracing，project =", os.environ.get("LANGSMITH_PROJECT", "default"))
            return True
    except Exception:
        pass
    return False


_langsmith_enabled = _try_init_langsmith()

from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, SystemMessage, ToolMessage
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

from app.services.llm_client import resolve_model, supports_thinking, init_chat_model_with_reasoning
from app.services.agent.prompts import get_core_prompts
from app.services.utils import normalize_tool_args
from app.services.agent.tools import (
    get_base_tools_for_mode,
    _current_chat_id,
    register_loop,
    is_stop_requested,
)
from app.services.agent.tools.callback import _current_model_name
from app.services.agent.tools.mcp_tools import load_mcp_tools, build_mcp_tools_prompt
from app.services.agent.skills import build_skills_prompt


# region LangGraph Agent（ReAct）


def _extract_text_content(content) -> str:
    """将 LLM 消息内容统一转换为纯文本，兼容 Claude 的结构化 content blocks。"""
    if content is None:
        return ""

    if isinstance(content, str):
        return content

    if isinstance(content, dict):
        # 常见块格式：{"type": "text", "text": "..."}
        text = content.get("text")
        if isinstance(text, str):
            return text
        # 兜底：部分实现可能用 content 字段
        fallback = content.get("content")
        return fallback if isinstance(fallback, str) else ""

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            item_text = _extract_text_content(item)
            if item_text:
                parts.append(item_text)
        return "".join(parts)

    # 其他类型不向前端输出，避免出现 [object Object]
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

    # Claude 风格: {"type": "thinking", "thinking": "..."}
    if block_type == "thinking":
        for key in ("thinking", "text", "content"):
            val = content.get(key)
            if isinstance(val, str) and val:
                return val

    # OpenAI 常见风格：reasoning / reasoning_content / summary_text
    if block_type in {"reasoning", "reasoning_content", "summary_text"}:
        for key in ("reasoning", "text", "content"):
            val = content.get(key)
            if isinstance(val, str) and val:
                return val

        # 某些返回会将推理摘要放在 summary 数组里
        summary = content.get("summary")
        if summary is not None:
            summary_text = _extract_thinking_content(summary)
            if summary_text:
                return summary_text

    # 兼容没有明确 type，但有 reasoning 字段的结构
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


def _prepare_tools_for_agent(tools: list, mcp_tool_names: set[str]) -> list:
    """包装工具，添加参数标准化、MCP 状态输出和停止信号检查。"""
    for tool in tools:
        if not hasattr(tool, "func") or tool.func is None:
            continue

        original_func = tool.func
        tool_name = tool.name
        is_mcp = tool_name in mcp_tool_names
        tool_args_schema = getattr(tool, "args_schema", None)

        def _make_wrapper(orig_fn, tname, mcp, args_schema):
            def wrapper(**kwargs):
                # 检查停止信号
                chat_id = _current_chat_id.get(None)
                if is_stop_requested(chat_id):
                    return "Operation cancelled by user"

                # MCP 工具状态输出（仅打印日志，不发往前端）
                if mcp:
                    preview = json.dumps(kwargs, ensure_ascii=False)
                    print(f"[Agent] 调用 MCP 工具: {tname}({preview[:200]})")

                # 参数标准化
                normalized = normalize_tool_args(tname, kwargs)
                required_fields: list[str] = []
                if mcp:
                    if isinstance(args_schema, dict):
                        required = args_schema.get("required")
                        if isinstance(required, list):
                            required_fields = [str(x) for x in required]
                    else:
                        # 兼容 pydantic v2 / v1 schema
                        model_fields = getattr(args_schema, "model_fields", None)
                        if isinstance(model_fields, dict):
                            for name, field in model_fields.items():
                                is_required = False
                                try:
                                    is_required = bool(field.is_required())
                                except Exception:
                                    is_required = False
                                if is_required:
                                    required_fields.append(str(name))
                        else:
                            legacy_fields = getattr(args_schema, "__fields__", None)
                            if isinstance(legacy_fields, dict):
                                for name, field in legacy_fields.items():
                                    if getattr(field, "required", False):
                                        required_fields.append(str(name))

                    missing_fields = [
                        field
                        for field in required_fields
                        if field not in normalized or normalized.get(field) in (None, "")
                    ]
                    if missing_fields:
                        provided_keys = sorted(list(normalized.keys())) if isinstance(normalized, dict) else []
                        return (
                            f"MCP tool {tname} argument validation failed: missing required params {missing_fields}. "
                            f"Required params: {required_fields}. Provided params: {provided_keys}. "
                            "Do not retry this tool with the same arguments; rebuild arguments from the tool schema first."
                        )

                try:
                    return orig_fn(**normalized)
                except Exception as e:
                    if mcp:
                        required_hint = f"Required params: {required_fields}. " if required_fields else ""
                        provided_keys = sorted(list(normalized.keys())) if isinstance(normalized, dict) else []
                        return (
                            f"MCP tool {tname} call failed: {e}. "
                            f"{required_hint}Provided params: {provided_keys}. "
                            "Rebuild arguments strictly according to the tool schema before retrying."
                        )
                    raise

            return wrapper

        tool.func = _make_wrapper(original_func, tool_name, is_mcp, tool_args_schema)

    return tools


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
        mode: 对话模式（agent/ask/plan）
        chat_id: WebSocket 会话 ID（用于工具回调）
        attached_files: 附件列表 [{file_id, filename, content_type, is_image}, ...]

    Yields:
        SSE 格式的流式输出
    """
    mode = (mode or "agent").strip().lower()
    if mode == "plan":
        mode = "agent"
    elif mode not in {"agent", "ask"}:
        mode = "agent"

    print("[Agent] 开始处理请求")
    print(f"[Agent] 模式: {mode}")
    print("[Agent] 配置: recursion_limit =", _AGENT_RECURSION_LIMIT)

    model_name = resolve_model(model or "auto")
    _thinking_enabled = supports_thinking(model_name)
    llm = init_chat_model_with_reasoning(model_name, enable_thinking=_thinking_enabled)
    if _thinking_enabled:
        print(f"[Agent] 🧠 模型 {model_name} 支持 thinking 模式，已启用")

    # ask 模式禁用 MCP；agent 模式按用户设置加载 MCP 动态工具
    mcp_clients = []  # 保持 MCP 客户端存活，防止 stdio 子进程被 GC 回收
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
    _prepare_tools_for_agent(tools, mcp_tool_names)
    print(f"[Agent] 已绑定 {[t.name for t in tools]}")

    # 构建系统提示（合并所有 system prompt 为单一字符串）
    system_parts = list(get_core_prompts(mode=mode))
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

    app = create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
        checkpointer=InMemorySaver(),
    )

    try:
        # 构建初始消息列表（create_agent 已注入 system_prompt，这里只构建记忆 + 用户消息）
        messages = []

        # 注入记忆（当前默认：摘要 + 短期；长期 RAG 暂停）
        from app.services.memory import build_memory_messages, _estimate_messages_tokens

        memory_result = build_memory_messages(
            history=history,
            current_message=message,
            llm=llm,
            session_id=chat_id,
            enable_long_term=False,
            return_meta=True,
        )
        memory_msgs, memory_meta = memory_result
        if memory_msgs:
            messages.extend(memory_msgs)
            print(f"[Agent] 注入 {len(memory_msgs)} 条记忆消息")
        if isinstance(memory_meta, dict) and memory_meta.get("triggered"):
            before_tokens = int(memory_meta.get("before_tokens_est", 0) or 0)
            after_tokens = int(memory_meta.get("after_tokens_est", 0) or 0)
            strategy = str(memory_meta.get("strategy", "none"))
            dropped = int(memory_meta.get("dropped_messages", 0) or 0)
            if strategy != "none":
                strategy_label = {
                    "llm_chain_extractor": "LLMChainExtractor",
                    "recent_keep_with_note": "截断保留",
                    "recent_keep": "截断保留",
                }.get(strategy, strategy)
                print(
                    f"[Agent] 🗜️ 启动压缩（{strategy_label}）: {before_tokens} -> {after_tokens} tokens, dropped={dropped}"
                )
            # 启动阶段不往前端发压缩状态，避免干扰首轮交互

        # 构建用户消息
        user_content = message
        if document_range:
            # 有文档范围时，指示 agent 调用 read_document 读取这些范围
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

        # 注入文档全局元信息（随用户提问发送）
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
        _agent_turn_count = 0  # ReAct 循环轮次计数
        _last_input_tokens = 0  # 最近一次 API 响应的真实 input_tokens（优先于本地估算）
        # 跟踪对话历史以估算动态 token
        _conversation_history: list = list(messages)

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
                        # 上下文超限：通知主循环触发重量重压缩，抛出异常让流退出
                        if _is_context_overflow_error(e):
                            print(f"[Agent] ⚠️ 上下文超限错误（{e}），触发被动重量重压缩")
                            asyncio.run_coroutine_threadsafe(queue.put(("context_overflow", str(e))), loop)
                            raise
                        # 仅在“首包前失败 + 可重试网络错误”时自动重试一次，避免重复输出
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

            # 上下文超限被动重压缩：收到 signal 后执行重量压缩，抛异常让 chat.py 重试
            if isinstance(stream_item, tuple) and stream_item[0] == "context_overflow":
                print(f"[Agent] ⚠️ 收到上下文超限信号，触发被动重量重压缩")
                from app.services.memory import compress_conversation_history_if_needed

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
                    # 将压缩后的 LangChain 消息转回 dict 列表，供 chat.py 更新 history 重试
                    updated_history = []
                    for m in compressed:
                        role = {"HumanMessage": "user", "AIMessage": "assistant", "SystemMessage": "system"}.get(
                            type(m).__name__, "assistant"
                        )
                        content_val = getattr(m, "content", "")
                        # 处理多模态内容
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

                # 处理 OpenAI/DeepSeek reasoning 模型的 reasoning_content（LangChain 已修复，会保留在 additional_kwargs）
                if isinstance(msg, AIMessageChunk):
                    reasoning_content = getattr(msg, "additional_kwargs", {}).get("reasoning_content")
                    if reasoning_content:
                        yield f"data: {json.dumps({'type': 'thinking', 'content': reasoning_content}, ensure_ascii=False)}\n\n"

                # 跟踪对话历史，记录最近一次 API 响应的真实 input_tokens
                # 注意：AIMessageChunk 是流式中间块，不追加到 _conversation_history
                # （避免本地估算不断膨胀），只从完整的 AIMessage 取 usage_metadata
                if isinstance(msg, AIMessage):
                    _conversation_history.append(msg)
                    # AIMessage 通常是完整响应，尝试从中获取 usage_metadata
                    usage = getattr(msg, "usage_metadata", None)
                    if isinstance(usage, dict) and "input_tokens" in usage and usage.get("input_tokens", 0) > 0:
                        _last_input_tokens = int(usage.get("input_tokens", 0))
                        # 发送更新后的 token 统计（让前端始终看到最新值）
                        from app.services.memory import MAX_CONTEXT_TOKENS

                        tokens_k = _last_input_tokens / 1000
                        max_tokens_k = MAX_CONTEXT_TOKENS / 1000
                        print(f"[Agent] 当前上下文: {tokens_k:.1f}k tokens")
                        yield f"data: {json.dumps({'type': 'token_stats', 'current_tokens': _last_input_tokens, 'max_tokens': MAX_CONTEXT_TOKENS}, ensure_ascii=False)}\n\n"
                elif isinstance(msg, AIMessageChunk):
                    # 只收集文本内容用于流式输出，不追加到 _conversation_history
                    normalized = _extract_text_content(msg.content)
                    if normalized:
                        _collected_text_parts.append(normalized)
                    # 从流式 chunk 的 usage_metadata 获取真实 input_tokens
                    usage = getattr(msg, "usage_metadata", None)
                    if isinstance(usage, dict) and "input_tokens" in usage and usage.get("input_tokens", 0) > 0:
                        _last_input_tokens = int(usage.get("input_tokens", 0))
                        # 发送更新后的 token 统计（让前端始终看到最新值）
                        from app.services.memory import MAX_CONTEXT_TOKENS

                        tokens_k = _last_input_tokens / 1000
                        max_tokens_k = MAX_CONTEXT_TOKENS / 1000
                        print(f"[Agent] 当前上下文: {tokens_k:.1f}k tokens")
                        yield f"data: {json.dumps({'type': 'token_stats', 'current_tokens': _last_input_tokens, 'max_tokens': MAX_CONTEXT_TOKENS}, ensure_ascii=False)}\n\n"
                elif isinstance(msg, ToolMessage):
                    # 将 ToolMessage 加入对话历史
                    _conversation_history.append(msg)
                    _agent_turn_count += 1
                    try:
                        from app.services.memory import MAX_CONTEXT_TOKENS

                        # 优先使用 API 真实 input_tokens，ToolMessage 本身很小可忽略
                        # 若真实值尚未拿到（首轮之前），回退到本地估算
                        current_tokens = (
                            _last_input_tokens
                            if _last_input_tokens > 0
                            else _estimate_messages_tokens(_conversation_history)
                        )
                        tokens_k = current_tokens / 1000
                        max_tokens_k = MAX_CONTEXT_TOKENS / 1000
                        print(f"[Agent] 轮次 {_agent_turn_count} | 当前上下文: {tokens_k:.1f}k tokens")
                        # 发送 token 统计给前端
                        yield f"data: {json.dumps({'type': 'token_stats', 'current_tokens': current_tokens, 'max_tokens': MAX_CONTEXT_TOKENS}, ensure_ascii=False)}\n\n"

                        # 使用 API 真实 input_tokens，压缩判断也以此为准（比本地估算更准确）
                        from app.services.memory import (
                            compress_conversation_history_if_needed,
                            _estimate_messages_tokens,
                        )

                        print(
                            f"[Agent] 压缩前 input_tokens: {_last_input_tokens}, _conversation_history 消息数: {len(_conversation_history)}"
                        )
                        compressed, meta = compress_conversation_history_if_needed(
                            _conversation_history,
                            llm=llm,
                            query=message,
                            history=history,  # 传原始 history 让 heavy compact 生成正确摘要
                            current_input_tokens=_last_input_tokens,
                        )
                        print(f"[Agent] 压缩后消息数: {len(compressed)}, meta={meta}")

                        # 提取压缩信息
                        light_meta = meta.get("light_compact", {})
                        heavy_meta = meta.get("heavy_compact", {})
                        hard_meta = meta.get("hard_truncate", {})

                        # 确定使用的策略
                        if light_meta.get("light_compact_triggered"):
                            strategy = "light_compact"
                            before = current_tokens
                            after = _estimate_messages_tokens(compressed)
                            dropped = light_meta.get("cleared_tool_results", 0)
                        elif heavy_meta.get("heavy_compact_triggered"):
                            strategy = "heavy_compact"
                            before = heavy_meta.get("before_tokens", current_tokens)
                            after = heavy_meta.get("after_tokens", 0)
                            dropped = 0
                        elif hard_meta.get("triggered"):
                            strategy = hard_meta.get("strategy", "hard_truncate")
                            before = hard_meta.get("before_tokens_est", 0)
                            after = hard_meta.get("after_tokens_est", 0)
                            dropped = hard_meta.get("dropped_messages", 0)
                        else:
                            strategy = "none"
                            before = 0
                            after = 0
                            dropped = 0

                        # 只有实际触发了压缩才打印；strategy=none 时跳过
                        if strategy != "none":
                            after_tokens_k = after / 1000
                            strategy_label = "轻量压缩" if strategy == "light_compact" else "重量压缩"
                            print(
                                f"[Agent] 🗜️ {strategy_label}完成: {before / 1000:.1f}k → {after_tokens_k:.1f}k tokens, dropped={dropped}"
                            )
                            # 重量压缩/Hard truncate 发前端（仅完成通知），轻量压缩仅后端 log
                            if strategy != "light_compact":
                                try:
                                    yield f"data: {json.dumps({'type': 'status', 'content': '🗜️ 上下文压缩完成'}, ensure_ascii=False)}\n\n"
                                except Exception:
                                    pass  # WebSocket 已断开，不影响主流程
                        else:
                            print("[Agent] 上下文压缩跳过（未超过阈值）")

                        # 无论是否压缩，都更新对话历史
                        _conversation_history.clear()
                        _conversation_history.extend(compressed)
                    except Exception as e:
                        print(f"[Agent] ⚠️ 上下文压缩失败: {e}")

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
                        if isinstance(content, str) and content.startswith("Sub-agent execution failed"):
                            yield f"data: {json.dumps({'type': 'status', 'content': content}, ensure_ascii=False)}\n\n"
                        elif isinstance(content, str) and content:
                            _collected_text_parts.append(content)
                        continue

                    if tool_name == "generate_document":
                        # 主 Agent 直接生成文档时，透传 JSON 给前端
                        try:
                            # content 可能是 dict（LangGraph 直接传递）或 str（序列化后的文本）
                            if isinstance(content, dict):
                                doc_json = content
                            elif isinstance(content, str):
                                try:
                                    doc_json = json.loads(content)
                                except json.JSONDecodeError:
                                    # str(dict) 产生的 Python 格式（单引号/True/False/None）
                                    import ast

                                    doc_json = ast.literal_eval(content)
                            else:
                                doc_json = None
                            if isinstance(doc_json, dict) and "paragraphs" in doc_json:
                                yield f"data: {json.dumps({'type': 'json', 'content': doc_json}, ensure_ascii=False)}\n\n"
                                continue
                        except Exception:
                            pass

                    # MCP 工具结果主渲染由 mcp_tools.py 通过 stream_writer 发送
                    # mcp_tool_call / mcp_tool_result 结构化事件到前端。
                    # 这里不再二次透传 ToolMessage 内容，避免重复/冲突展示。
                    if tool_name in mcp_tool_names:
                        print(
                            f"[Agent] MCP 工具 {tool_name} 返回类型: {type(content).__name__}, 内容预览: {str(content)[:200]}"
                        )
                    continue

                # 处理结构化 content blocks（兼容 Claude/OpenAI thinking/reasoning）
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
                                    yield f"data: {json.dumps({'type': 'text', 'content': text}, ensure_ascii=False)}\n\n"
                    continue

                # 普通文本输出（非 thinking 模式）
                normalized_text = _extract_text_content(content)
                if normalized_text:
                    _collected_text_parts.append(normalized_text)
                    yield f"data: {json.dumps({'type': 'text', 'content': normalized_text}, ensure_ascii=False)}\n\n"

            elif input_type == "custom":
                # stream_writer 的输出（工具的状态消息）
                print(f"[Agent] 自定义输出: {chunk}")
                if chunk:
                    if isinstance(chunk, dict):
                        yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                    else:
                        yield f"data: {json.dumps({'type': 'status', 'content': str(chunk)}, ensure_ascii=False)}\n\n"

        # 只在 agent 模式下且期望生成文档时显示警告
        if mode == "agent" and not has_tool_result and document_range:
            yield f"data: {json.dumps({'type': 'status', 'content': '⚠️ 没有检测到调用工具，模型可能不支持'}, ensure_ascii=False)}\n\n"

        # [已移除] 长期记忆存储
        # store_conversation_to_long_term() 现为 stub 函数，无实际效果
        # 对话历史通过 build_memory_messages 中的短期/总结记忆机制管理

        yield "data: [DONE]\n\n"

    except Exception as e:
        print(f"[Agent Error] {e}")
        traceback.print_exc()
        yield f"data: {json.dumps({'type': 'text', 'content': f'Error: {str(e)}'}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
