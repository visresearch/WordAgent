"""文档处理 Agent - 使用 LangChain create_agent + 中间件 + 流式输出。"""

import asyncio
import concurrent.futures
import json
import re
import threading
import time
import traceback
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import AgentState
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    HumanMessage,
    ToolMessage,
)
from langchain_core.messages.utils import count_tokens_approximately

from app.core.logging import get_logger
from app.services.agent.prompts import build_user_prompt, get_core_prompts
from app.services.agent.skills import build_skills_prompt
from app.services.agent.tools import (
    _current_chat_id,
    _current_model_name,
    _current_request_context,
    build_mcp_tools_prompt,
    get_base_tools_for_mode,
    is_stop_requested,
    load_mcp_tools,
    register_loop,
    register_stop_event,
    unregister_stop_event,
)
from app.services.document import (
    build_document_name_by_id,
    format_document_range_line,
    normalize_document_meta,
)
from app.services.llm_client import init_chat_model_with_reasoning, resolve_model, supports_thinking
from app.services.memory import build_runtime_thread_id
from app.services.human_input import pending_questions
from app.services.middleware import MAX_CONTEXT_TOKENS, build_agent_middleware
from app.services.tools.tool_log import build_tool_json, set_current_tool_log
from app.services.token_usage import normalize_usage_metadata
from app.services.utils import try_init_langsmith

logger = get_logger(__name__)

MAX_CHECKPOINT_IMAGE_BYTES = 512 * 1024


def _ocr_attachment_context(project_paths: list[str]) -> str:
    """Supply image text directly when an image must be sent to a text-only model."""
    from app.services.plugins.manager import has_capability

    if not project_paths or not has_capability("ocr"):
        return ""
    from app.services.tools.file_tools import _ocr_image_text, _resolve_project_path

    lines = ["[OCR text from attached images]"]
    for path in project_paths:
        try:
            image = _resolve_project_path(path, must_exist=True)
            lines.append(f"{path}:\n{_ocr_image_text(image)}")
        except (OSError, ValueError) as exc:
            lines.append(f"{path}: OCR unavailable ({exc})")
    return "\n".join(lines)


class WordAgentState(AgentState):
    # Keep the original document/model context while a human clarification is pending.
    request_context: dict


def _message_token_usage(message) -> dict[str, int]:
    """Merge normalized and provider-specific raw usage from a streamed message."""
    result = normalize_usage_metadata(getattr(message, "usage_metadata", None))
    response_metadata = getattr(message, "response_metadata", None)
    if not isinstance(response_metadata, dict):
        return result
    for field in ("raw_token_usage", "token_usage", "usage"):
        fallback = normalize_usage_metadata(response_metadata.get(field))
        for key in result:
            if result[key] <= 0 and fallback[key] > 0:
                result[key] = fallback[key]
    return result


def _attachment_size_bytes(attachment: dict, file_id: str) -> int | None:
    """读取附件大小，供 Checkpoint 内联图片保护使用。"""
    raw_size = attachment.get("size")
    try:
        size = int(raw_size)
        if size >= 0:
            return size
    except (TypeError, ValueError):
        pass

    try:
        from app.api.routes.files import get_file_path

        file_path = get_file_path(file_id)
        return file_path.stat().st_size if file_path else None
    except OSError:
        return None


def _summarize_custom_event(chunk: Any) -> str:
    """Return a compact log line for stream_writer custom events."""
    if not isinstance(chunk, dict):
        text = str(chunk)
        return text if len(text) <= 300 else text[:300] + "..."

    event_type = chunk.get("type", "?")
    parts = [f"type={event_type}"]

    tool_name = chunk.get("toolName")
    if tool_name:
        parts.append(f"tool={tool_name}")

    if event_type == "json":
        content = chunk.get("content")
        if isinstance(content, dict):
            blocks = content.get("paragraphs")
            styles = content.get("styles")
            paragraphs = (
                [block for block in blocks if isinstance(block, dict) and "runs" in block]
                if isinstance(blocks, list)
                else []
            )
            table_count = sum(
                len(block.get("tables", []))
                for block in blocks or []
                if isinstance(block, dict) and isinstance(block.get("tables"), list)
            )
            parts.append(f"paragraphs={len(paragraphs)}")
            parts.append(f"tables={table_count}")
            parts.append(f"styles={len(styles) if isinstance(styles, dict) else 0}")
            if "insertParaID" in content:
                parts.append(f"insertParaID={content.get('insertParaID')}")
            if "docId" in content:
                parts.append(f"docId={content.get('docId')}")
    elif event_type in {"mcp_tool_call", "tool_call"}:
        args = chunk.get("args")
        if isinstance(args, dict):
            parts.append(f"args={list(args.keys())}")
    elif event_type in {"mcp_tool_result", "tool_result"}:
        parts.append(f"length={chunk.get('outputLength', 0)}")
        parts.append(f"truncated={bool(chunk.get('truncated'))}")
        if chunk.get("isError"):
            parts.append("error=true")
    elif event_type in {
        "read_document",
        "read_complete",
        "search_document",
        "query_complete",
        "delete_document",
        "edit_document",
        "edit_complete",
        "insert_break",
        "create_document",
        "generate_complete",
    }:
        content = chunk.get("content")
        if content:
            parts.append(str(content))
        for key in (
            "docId",
            "insertParaID",
            "paraID",
            "breakType",
            "startParaIndex",
            "endParaIndex",
            "startParaID",
            "endParaID",
        ):
            if key in chunk and chunk.get(key) is not None:
                parts.append(f"{key}={chunk.get(key)}")
    else:
        keys = sorted(str(k) for k in chunk)
        parts.append(f"keys={keys}")

    return " ".join(parts)


class ContextOverflowError(Exception):
    """单智能体在摘要后仍然超过模型上下文限制。"""


_langsmith_enabled = try_init_langsmith()


_THINK_TAG_RE = re.compile(r"<think(?:ing)?\b[^>]*>(.*?)</think(?:ing)?>", re.IGNORECASE | re.DOTALL)
_OPEN_THINK_TAG_RE = re.compile(r"<think(?:ing)?\b[^>]*>(.*)$", re.IGNORECASE | re.DOTALL)
_CLOSE_THINK_TAG_RE = re.compile(r"</think(?:ing)?>", re.IGNORECASE)


def _split_tagged_thinking_text(text: str) -> tuple[str, str]:
    """Split inline <think>...</think> text from visible assistant content."""
    if not text:
        return "", ""

    thinking_parts: list[str] = []

    def _collect(match: re.Match) -> str:
        inner = match.group(1).strip()
        if inner:
            thinking_parts.append(inner)
        return ""

    visible = _THINK_TAG_RE.sub(_collect, text)
    open_match = _OPEN_THINK_TAG_RE.search(visible)
    if open_match:
        inner = open_match.group(1).strip()
        if inner:
            thinking_parts.append(inner)
        visible = visible[: open_match.start()]

    visible = _CLOSE_THINK_TAG_RE.sub("", visible)
    thinking = "\n".join(part for part in thinking_parts if part).strip()
    return visible, thinking


def _extract_text_content(content) -> str:
    """将 LLM 消息内容统一转换为纯文本，并剥离内联 thinking 标签。"""
    if content is None:
        return ""

    if isinstance(content, str):
        visible, _thinking = _split_tagged_thinking_text(content)
        return visible

    if isinstance(content, dict):
        text = content.get("text")
        if isinstance(text, str):
            return _extract_text_content(text)
        fallback = content.get("content")
        return _extract_text_content(fallback) if isinstance(fallback, str) else ""

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            item_text = _extract_text_content(item)
            if item_text:
                parts.append(item_text)
        return "".join(parts)

    return ""


def _extract_tagged_thinking_content(content) -> str:
    """Extract inline <think>...</think> content from plain text blocks."""
    if content is None:
        return ""
    if isinstance(content, str):
        _visible, thinking = _split_tagged_thinking_text(content)
        return thinking
    if isinstance(content, dict):
        text = content.get("text")
        if isinstance(text, str):
            return _extract_tagged_thinking_content(text)
        fallback = content.get("content")
        return _extract_tagged_thinking_content(fallback) if isinstance(fallback, str) else ""
    if isinstance(content, list):
        parts = [_extract_tagged_thinking_content(item) for item in content]
        return "\n".join(part for part in parts if part)
    return ""


def _extract_latest_final_ai_text(messages: list) -> str:
    """
    从对话消息中提取最后一条“最终回答”文本。

    规则：
    - 只看 AIMessage
    - 忽略仍在发起工具调用的中间 AIMessage（tool_calls 非空）
    - 取最后一条非空文本
    """
    for msg in reversed(messages):
        if not isinstance(msg, AIMessage):
            continue

        tool_calls = getattr(msg, "tool_calls", None)
        if isinstance(tool_calls, list) and tool_calls:
            continue

        text = _extract_text_content(getattr(msg, "content", "")).strip()
        if text:
            return text

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


def _friendly_agent_error_message(exc: Exception) -> str:
    """把常见上游模型错误转换为可操作的用户提示。"""
    text = str(exc)
    lowered = text.lower()
    if "无效工具调用参数" in text or "invalid tool call" in lowered:
        return "模型生成的工具参数格式无效，已自动重新生成；仍失败时请拆分文档内容后重试"
    if "insufficient balance" in lowered or ("402" in lowered and "balance" in lowered):
        return "模型服务余额不足，请充值当前模型供应商账户，或切换到其他可用模型后重试"
    return f"模型调用失败：{text}"


def _is_image_input_unsupported_error(exc: Exception) -> bool:
    """判断是否是模型端点不支持图像输入错误。"""
    text = str(exc).lower()
    image_signals = [
        "no endpoints found that support image input",
        "does not support image input",
        "does not support images",
        "image input is not supported",
        "unsupported image input",
        "unknown variant image_url",
        "image_url",
        "expected text",
    ]
    return any(sig in text for sig in image_signals)


# region 主处理函数


async def process_writing_request_stream(
    message: str,
    document_range: list[dict] | None = None,
    document_meta: dict | None = None,
    model: str | None = None,
    provider: str | None = None,
    mode: str | None = None,
    chat_id: str | None = None,
    attached_files: list[dict] | None = None,
    enable_thinking: bool = True,
    session_id: str | None = None,
    checkpointer=None,
    resume_command=None,
    resume_tool_log: list[dict] | None = None,
) -> AsyncGenerator[str, None]:
    """
    使用 LangChain create_agent 处理写作请求并流式输出。

    重构要点：
    - Todo、工具参数规范化、日志、结果压缩和失败重试均由中间件处理
    - 单智能体短期记忆和摘要由 Checkpointer + SummarizationMiddleware 管理
    - 保留长期记忆、MCP 自定义事件和 thinking 流式输出
    """
    mode = (mode or "agent").strip().lower()
    if mode not in {"agent", "ask"}:
        mode = "agent"

    logger.info("[Agent] 开始处理请求")
    logger.info(f"[Agent] 模式: {mode}")
    logger.info(f"[Agent] 深度思考: {enable_thinking}")

    model_name = resolve_model(model or "auto", provider or "")
    _thinking_enabled = enable_thinking and supports_thinking(model_name)
    llm = init_chat_model_with_reasoning(model_name, enable_thinking=_thinking_enabled)

    # agent/ask 模式按用户设置加载 MCP 动态工具
    mcp_clients = []
    if mode in {"agent", "ask"}:
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
    logger.info(f"[Agent] 已注册 {len(tools)} 个业务工具，中间件将追加 write_todos")
    logger.debug(f"[Agent] 工具列表: {[t.name for t in tools]}")

    # 系统提示只保留模式规则及工具/技能说明，不混入逐轮变化的用户上下文。
    system_parts = list(get_core_prompts(mode=mode))

    if mode in {"agent", "ask"}:
        mcp_prompt = build_mcp_tools_prompt(mcp_tools)
        if mcp_prompt:
            system_parts.append(mcp_prompt)
    skills_prompt = build_skills_prompt()
    if skills_prompt:
        system_parts.append(skills_prompt)
    system_prompt = "\n\n".join(system_parts)

    app = create_agent(
        state_schema=WordAgentState,
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
        middleware=build_agent_middleware(
            summary_model=llm,
            system_prompt=system_prompt,
            tools=tools,
        ),
        checkpointer=checkpointer,
    )
    tool_log: list[dict] = list(resume_tool_log or [])
    meta_list = normalize_document_meta(document_meta)
    document_name_by_id = build_document_name_by_id(meta_list)
    document_meta_for_context = meta_list[0] if len(meta_list) == 1 else meta_list
    executor: concurrent.futures.ThreadPoolExecutor | None = None
    stream_future: concurrent.futures.Future | None = None
    stop_event = threading.Event()
    if chat_id:
        register_stop_event(chat_id, stop_event)
        # The WebSocket may have been stopped before the worker reached this
        # point; inherit that already-recorded stop request.
        if is_stop_requested(chat_id):
            stop_event.set()

    try:
        # Checkpointer 自动恢复历史；本轮只提交当前用户消息。
        messages = []

        # 每轮只读取一次动态上下文，图片降级/网络重试复用相同内容。
        from app.services.llm_client import get_custom_prompt
        from app.services.memory import build_long_term_memory_prompt, is_long_term_memory_enabled

        long_term_prompt = ""
        if is_long_term_memory_enabled():
            long_term_prompt = build_long_term_memory_prompt()
            if long_term_prompt:
                logger.info("[Agent] 已将长期记忆注入用户消息")
        user_prompt_options = {
            "custom_prompt": get_custom_prompt(),
            "request_time": datetime.now().astimezone(),
            "long_term_memory": long_term_prompt,
        }
        context_sections = []
        if document_range:
            # 构建文档范围描述
            range_lines = []
            for r in document_range:
                range_lines.append(format_document_range_line(r, document_name_by_id))

            if mode == "ask":
                selection_context = (
                    "[Selected Document Ranges]\n"
                    "User has selected the following document content:\n"
                    + "\n".join(f"  - {line}" for line in range_lines)
                    + "\nPlease answer based on the above content."
                )
            else:
                selection_context = (
                    "[Selected Document Ranges]\n"
                    "Please process based on the user-selected document content:\n"
                    + "\n".join(f"  - {line}" for line in range_lines)
                )
            context_sections.append(selection_context)
            logger.info(f"[Agent] 文档范围: {document_range}")

        # 注入文档全局元信息（支持多文档）
        if meta_list:
            # 使用 JSON 格式输出元信息（紧凑模式，不换行）
            meta_json = json.dumps(meta_list, ensure_ascii=False, separators=(",", ":"))
            context_sections.append(
                "[Document Global Metadata]"
                "\nThe following fields come from frontend document state and are not body content."
                f"\n{meta_json}"
                "\nUse these metadata fields in task analysis. The first document in the array is the active document the user is currently viewing."
                "\nIf the active document has isEmpty=true, treat it as a blank/new document: for the first generate_document call, use the active documentId as docId and set insertParaID=0. Do not call read_document just to obtain the empty placeholder paragraph ID."
            )
        # 处理附件
        image_content_parts = []
        image_project_paths = []
        file_reference_parts = []
        attached_image_count = 0
        if attached_files:
            from app.api.routes.files import read_file_as_base64

            for f in attached_files:
                file_id = f.get("file_id", "")
                filename = f.get("filename", "")
                content_type = f.get("content_type", "")
                is_image = f.get("is_image", False)
                project_path = f.get("project_path", f"uploads/{file_id}" if file_id else "")

                if is_image:
                    attached_image_count += 1
                    if project_path:
                        image_project_paths.append(project_path)
                    line = f"- {filename} [image] | project_path={project_path or '(unknown)'}"
                    file_reference_parts.append(line)

                    image_size = _attachment_size_bytes(f, file_id)
                    if image_size is not None and image_size <= MAX_CHECKPOINT_IMAGE_BYTES:
                        b64 = read_file_as_base64(file_id)
                    else:
                        b64 = None
                        logger.warning(
                            "[Agent] 图片未内联到 Checkpoint，改用项目路径: %s (%s bytes)",
                            filename,
                            image_size if image_size is not None else "unknown",
                        )
                    if b64:
                        image_content_parts.append(
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:{content_type};base64,{b64}"},
                            }
                        )
                        logger.info(f"[Agent] 🖼️ 附件图片: {filename}")
                else:
                    line = f"- {filename} | project_path={project_path or '(unknown)'}"
                    file_reference_parts.append(line)
                    logger.info(f"[Agent] 📄 附件文件引用: {filename} -> {project_path}")

        if file_reference_parts:
            context_sections.append(
                "[Attached Files]"
                "\nFiles are already uploaded under wence_data/project."
                "\nDo NOT assume file contents from metadata."
                "\nOnly project_path is shown; it is relative to that project root (e.g. uploads/...)."
                "\nWhen non-image file content is needed, call `read_file` with exactly that project_path string."
                "\nFor generate_document image runs, you may set url to the same project-relative path;"
                " the server resolves it to an absolute local path for the Word/WPS client."
                "\n" + "\n".join(file_reference_parts)
            )

        image_context = ""
        if image_content_parts:
            image_context = "Attached images are also provided as direct model image inputs in this request. Use the visual input directly; do not call `read_file` for these image files unless the user explicitly asks for OCR text or file metadata."

        text_only_image_context = ""
        if attached_image_count:
            text_only_image_context = (
                "Direct image input is unavailable in this request. Use the OCR text below when provided; "
                "otherwise call `read_file(path)` on the image project_path when image content is needed."
            )

        image_user_content = build_user_prompt(
            message, context_sections=context_sections, image_context=image_context, **user_prompt_options
        )
        text_only_user_content = build_user_prompt(
            message, context_sections=context_sections, image_context=text_only_image_context, **user_prompt_options
        )
        if attached_image_count and not image_content_parts:
            ocr_context = await asyncio.to_thread(_ocr_attachment_context, image_project_paths)
            if ocr_context:
                text_only_user_content = build_user_prompt(
                    message,
                    context_sections=context_sections + [ocr_context],
                    image_context=text_only_image_context,
                    **user_prompt_options,
                )

        # 构建 HumanMessage
        message_id = str(uuid.uuid4())
        if image_content_parts:
            human_content = [{"type": "text", "text": image_user_content}] + image_content_parts
            messages.append(HumanMessage(content=human_content, id=message_id))
        else:
            messages.append(HumanMessage(content=text_only_user_content, id=message_id))
        text_only_messages = list(messages[:-1]) + [HumanMessage(content=text_only_user_content, id=message_id)]

        logger.debug(f"[Agent] 消息数量: {len(messages)}")

        # 获取事件循环
        loop = asyncio.get_running_loop()
        if chat_id:
            register_loop(chat_id, loop)

        # 队列用于线程间传递流式数据
        queue: asyncio.Queue = asyncio.Queue()
        has_tool_result = bool(resume_tool_log)
        _collected_text_parts: list[str] = []
        _assistant_text_for_memory_parts: list[str] = []
        _has_streamed_text_chunks = False
        _pending_text_chunks: list[str] = []
        _agent_turn_count = 0
        _last_input_tokens = 0
        _request_token_usage = {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0}
        _chunk_token_usage = {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0}
        _conversation_history: list = list(messages)
        _waiting_for_user = False

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
                        "has_document_meta": bool(meta_list),
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
                set_current_tool_log(tool_log)
                _current_model_name.set(model_name)
                # 设置请求上下文，供工具函数获取 document_meta
                _current_request_context.set(
                    {
                        "document_meta": document_meta_for_context,
                        "document_range": document_range,
                    }
                )

                _thread_id = build_runtime_thread_id(session_id, chat_id)
                _config = {
                    "configurable": {"thread_id": _thread_id},
                }
                if langsmith_config:
                    _config.update(langsmith_config)

                stream_kwargs = {
                    "input": resume_command
                    if resume_command is not None
                    else {
                        "messages": messages,
                        "request_context": {
                            "document_range": document_range,
                            "document_meta": document_meta,
                            "model": model,
                            "provider": provider,
                            "mode": mode,
                            "enable_thinking": enable_thinking,
                        },
                    },
                    "stream_mode": ["messages", "custom", "updates"],
                    "config": _config,
                }

                max_attempts = 3 if image_content_parts else 2
                image_fallback_applied = False
                for attempt in range(1, max_attempts + 1):
                    if stop_event.is_set():
                        break
                    has_any_stream_item = False
                    try:
                        response = app.stream(**stream_kwargs)

                        for stream_item in response:
                            has_any_stream_item = True
                            if stop_event.is_set() or (chat_id and is_stop_requested(chat_id)):
                                logger.warning(f"[Agent] ⛔ 检测到停止信号，结束流式处理 (session={chat_id})")
                                break
                            asyncio.run_coroutine_threadsafe(queue.put(stream_item), loop)

                        asyncio.run_coroutine_threadsafe(queue.put(None), loop)
                        return
                    except Exception as e:
                        if (
                            resume_command is None
                            and image_content_parts
                            and not image_fallback_applied
                            and _is_image_input_unsupported_error(e)
                        ):
                            image_fallback_applied = True
                            logger.warning("[Agent] ⚠️ 当前端点不支持图像输入，自动降级为文本模式重试")
                            ocr_context = _ocr_attachment_context(image_project_paths)
                            fallback_messages = text_only_messages
                            if ocr_context:
                                fallback_content = build_user_prompt(
                                    message,
                                    context_sections=context_sections + [ocr_context],
                                    image_context=text_only_image_context,
                                    **user_prompt_options,
                                )
                                fallback_messages = list(messages[:-1]) + [
                                    HumanMessage(content=fallback_content, id=message_id)
                                ]
                            stream_kwargs["input"] = {**stream_kwargs["input"], "messages": fallback_messages}
                            continue

                        if _is_context_overflow_error(e):
                            logger.error(f"[Agent] ⚠️ 摘要后上下文仍超限（{e}）")
                            raise
                        if attempt < max_attempts and (not has_any_stream_item) and _is_transient_stream_error(e):
                            logger.error(f"[Agent] ⚠️ 流式连接异常（第 {attempt} 次）: {e}，准备重试")
                            if stop_event.wait(0.5):
                                break
                            continue
                        raise
            except Exception as e:
                event_type = "context_overflow" if _is_context_overflow_error(e) else "error"
                asyncio.run_coroutine_threadsafe(queue.put((event_type, str(e))), loop)

        # 在线程池中启动
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        stream_future = executor.submit(run_stream)

        # 从队列中消费流式数据
        while True:
            if stop_event.is_set() and queue.empty():
                break
            stream_item = await queue.get()

            if stream_item is None:
                break

            if isinstance(stream_item, tuple) and stream_item[0] == "error":
                raise Exception(stream_item[1])

            # SummarizationMiddleware 仍无法处理的上下文超限只作为最终兜底报错。
            if isinstance(stream_item, tuple) and stream_item[0] == "context_overflow":
                logger.error("[Agent] SummarizationMiddleware 执行后上下文仍然超限")
                raise ContextOverflowError("上下文仍超出模型限制，请新建会话或减少输入内容")

            if not isinstance(stream_item, tuple):
                continue

            input_type, chunk = stream_item

            if input_type == "updates" and isinstance(chunk, dict) and chunk.get("__interrupt__"):
                pending = pending_questions(chunk["__interrupt__"])
                if pending:
                    _waiting_for_user = True
                    question_text = "\n".join(item["question"] for item in pending["questions"])
                    _assistant_text_for_memory_parts.append(question_text)
                    tool_log.extend(
                        {"tool": "ask_user", "input": item, "output": None, "status": "waiting"}
                        for item in pending["questions"]
                    )
                    yield f"data: {json.dumps(pending, ensure_ascii=False)}\n\n"

            if input_type == "messages":
                if not chunk or len(chunk) == 0:
                    continue
                msg, metadata = chunk
                if isinstance(msg, (AIMessage, AIMessageChunk)) and metadata.get("langgraph_node") != "model":
                    logger.debug(
                        "[Agent] 过滤内部模型流: node=%s source=%s",
                        metadata.get("langgraph_node"),
                        metadata.get("lc_source"),
                    )
                    continue
                content = msg.content

                # reasoning_content 透传（OpenAI/DeepSeek）
                if isinstance(msg, AIMessageChunk):
                    reasoning_content = getattr(msg, "additional_kwargs", {}).get("reasoning_content")
                    if reasoning_content:
                        yield f"data: {json.dumps({'type': 'thinking', 'content': reasoning_content}, ensure_ascii=False)}\n\n"

                # AIMessage：完整响应，追踪历史和 token
                if isinstance(msg, AIMessage):
                    _conversation_history.append(msg)
                    normalized_usage = _message_token_usage(msg)
                    for key in _request_token_usage:
                        _request_token_usage[key] += normalized_usage[key]
                    if normalized_usage["input_tokens"] > 0:
                        _last_input_tokens = normalized_usage["input_tokens"]
                        tokens_k = _last_input_tokens / 1000
                        logger.info(f"[Agent] 当前上下文: {tokens_k:.1f}k tokens")
                        yield f"data: {json.dumps({'type': 'token_stats', 'current_tokens': _last_input_tokens, 'max_tokens': MAX_CONTEXT_TOKENS}, ensure_ascii=False)}\n\n"

                    if getattr(msg, "tool_calls", None):
                        _pending_text_chunks.clear()
                        continue

                # AIMessageChunk：流式中间块，先缓冲文本；如果本轮随后发起工具调用则丢弃
                if isinstance(msg, AIMessageChunk):
                    # Some OpenAI-compatible providers attach usage to the final
                    # streaming chunk instead of emitting a complete AIMessage.
                    normalized_chunk_usage = _message_token_usage(msg)
                    if any(normalized_chunk_usage.values()):
                        for key in _chunk_token_usage:
                            _chunk_token_usage[key] += normalized_chunk_usage[key]
                    if getattr(msg, "tool_call_chunks", None) or getattr(msg, "tool_calls", None):
                        _pending_text_chunks.clear()
                        continue
                    tagged_thinking = _extract_tagged_thinking_content(msg.content)
                    if tagged_thinking:
                        yield f"data: {json.dumps({'type': 'thinking', 'content': tagged_thinking}, ensure_ascii=False)}\n\n"
                    normalized = _extract_text_content(msg.content)
                    if normalized:
                        _pending_text_chunks.append(normalized)

                # ToolMessage：工具执行结果
                if isinstance(msg, ToolMessage):
                    _pending_text_chunks.clear()
                    _conversation_history.append(msg)
                    _agent_turn_count += 1
                    tool_name = getattr(msg, "name", "")
                    has_tool_result = True

                    if tool_name == "run_sub_agent":
                        logger.info("[Agent] ⏭️ 跳过 run_sub_agent 工具返回值")
                        if isinstance(content, str) and content.startswith("Sub-agent execution failed"):
                            yield f"data: {json.dumps({'type': 'status', 'content': content}, ensure_ascii=False)}\n\n"
                        elif isinstance(content, str) and content:
                            _collected_text_parts.append(content)
                        continue

                    # MCP 工具日志
                    if tool_name in mcp_tool_names:
                        logger.info(
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
                                    raw_text = block.get("text", "") or block.get("content", "")
                                    tagged_thinking = _extract_tagged_thinking_content(raw_text)
                                    if tagged_thinking:
                                        yield f"data: {json.dumps({'type': 'thinking', 'content': tagged_thinking}, ensure_ascii=False)}\n\n"
                                    text = _extract_text_content(raw_text)
                                    if text:
                                        _collected_text_parts.append(text)
                                        if not _has_streamed_text_chunks:
                                            _pending_text_chunks.clear()
                                            _assistant_text_for_memory_parts.append(text)
                                            yield f"data: {json.dumps({'type': 'text', 'content': text}, ensure_ascii=False)}\n\n"
                        continue

                    # 普通文本
                    tagged_thinking = _extract_tagged_thinking_content(content)
                    if tagged_thinking:
                        yield f"data: {json.dumps({'type': 'thinking', 'content': tagged_thinking}, ensure_ascii=False)}\n\n"
                    normalized_text = _extract_text_content(content)
                    if not normalized_text and _pending_text_chunks:
                        normalized_text = "".join(_pending_text_chunks).strip()
                    if normalized_text:
                        _pending_text_chunks.clear()
                        _collected_text_parts.append(normalized_text)
                        if not _has_streamed_text_chunks:
                            _assistant_text_for_memory_parts.append(normalized_text)
                            yield f"data: {json.dumps({'type': 'text', 'content': normalized_text}, ensure_ascii=False)}\n\n"

            elif input_type == "custom":
                # stream_writer 输出（工具状态消息）
                logger.info(f"[Agent] 事件: {_summarize_custom_event(chunk)}")
                logger.debug(f"[Agent] 自定义输出: {chunk}")
                if chunk:
                    if isinstance(chunk, dict):
                        yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                    else:
                        yield f"data: {json.dumps({'type': 'status', 'content': str(chunk)}, ensure_ascii=False)}\n\n"

        if _pending_text_chunks:
            pending_text = "".join(_pending_text_chunks).strip()
            _pending_text_chunks.clear()
            if pending_text:
                _collected_text_parts.append(pending_text)
                _assistant_text_for_memory_parts.append(pending_text)
                yield f"data: {json.dumps({'type': 'text', 'content': pending_text}, ensure_ascii=False)}\n\n"

        # 警告
        if mode == "agent" and not has_tool_result and document_range and not _waiting_for_user:
            yield f"data: {json.dumps({'type': 'status', 'content': '⚠️ 没有检测到调用工具，模型可能不支持'}, ensure_ascii=False)}\n\n"

        yield "data: [DONE]\n\n"

        # 流式结束后，yield 完整对话用于长期记忆提取
        # 构造用户消息内容（包含文档上下文）
        user_content = message
        if document_range:
            range_lines = []
            for r in document_range:
                range_lines.append(format_document_range_line(r, document_name_by_id))
            user_content = f"{message}\n\nPlease process based on the user-selected document content:\n" + "\n".join(
                f"  - {line}" for line in range_lines
            )

        # 构造 AI 回复内容：
        # 1) 优先使用“实际流给前端”的 text 片段，确保与用户最终看到的一致；
        # 2) 兜底使用最终 AIMessage；
        # 3) 最后再回退到历史拼接（兼容极端场景）。
        assistant_content = "".join(_assistant_text_for_memory_parts).strip()
        if not assistant_content:
            assistant_content = _extract_latest_final_ai_text(_conversation_history).strip()
        if not assistant_content:
            assistant_content = "".join(_collected_text_parts).strip()

        # 返回完整对话（供记忆提取使用）和工具日志（供后端持久化使用）
        conversation_for_memory = {"user": user_content, "assistant": assistant_content}
        final_token_usage = dict(_request_token_usage if any(_request_token_usage.values()) else _chunk_token_usage)
        # A few OpenAI-compatible gateways omit usage in streaming responses.
        # Keep the dashboard useful with a conservative LangChain estimate.
        if final_token_usage["input_tokens"] <= 0:
            final_token_usage["input_tokens"] = count_tokens_approximately(messages, use_usage_metadata_scaling=False)
        if final_token_usage["output_tokens"] <= 0 and assistant_content:
            final_token_usage["output_tokens"] = count_tokens_approximately(
                [AIMessage(content=assistant_content)], use_usage_metadata_scaling=False
            )
        logger.info(
            "[Agent] Token usage: input=%s output=%s cache_read=%s",
            final_token_usage["input_tokens"],
            final_token_usage["output_tokens"],
            final_token_usage["cached_tokens"],
        )
        yield f"__token_usage__: {json.dumps(final_token_usage, ensure_ascii=False)}\n\n"
        yield f"__memory_conversation__: {json.dumps(conversation_for_memory, ensure_ascii=False)}\n\n"
        yield f"__tool_json__: {json.dumps(build_tool_json(tool_log), ensure_ascii=False)}\n\n"

    except ContextOverflowError:
        raise
    except Exception as e:
        logger.error(f"[Agent Error] {e}")
        traceback.print_exc()
        yield f"data: {json.dumps({'type': 'error', 'content': _friendly_agent_error_message(e)}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
    finally:
        stop_event.set()
        if stream_future is not None:
            stream_future.cancel()
        if executor is not None:
            executor.shutdown(wait=False, cancel_futures=True)
        if chat_id:
            unregister_stop_event(chat_id, stop_event)
