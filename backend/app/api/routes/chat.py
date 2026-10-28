"""
聊天处理路由
"""

import asyncio
import json
import traceback
import uuid
from contextlib import aclosing, suppress

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.db import AsyncSessionLocal
from app.core.logging import get_logger
from app.services.agent.agent import (
    ContextOverflowError,
)
from app.services.agent.agent import (
    process_writing_request_stream as single_agent_stream,
)
from app.services.agent.tools import (
    cleanup_tool_request,
    create_tool_request,
    request_stop,
    submit_tool_response,
)
from app.services.human_input import answer_command, load_pending_questions
from app.services.memory import build_runtime_thread_id, single_agent_thread_lock
from app.services.session_service import SessionService
from app.services.token_usage import record_token_usage
from app.services.utils import _get_env_int, normalize_uuid

logger = get_logger(__name__)
router = APIRouter()

# Idle watchdog 阈值（秒）：超过 IDLE_WARN_SECONDS 没有 chunk 时，
# 给前端一条"正在思考下一步"提示；超过 IDLE_ABORT_SECONDS 仍无 chunk 时，
# 强制停止 LLM 调用并断开 WebSocket。
IDLE_WARN_SECONDS = _get_env_int("WORDAGENT_IDLE_WARN_SECONDS", 100)
IDLE_ABORT_SECONDS = max(
    IDLE_WARN_SECONDS + 1,
    _get_env_int("WORDAGENT_IDLE_ABORT_SECONDS", 300),
)
# 应用层 keepalive：长 LLM 思考期间，每隔 KEEPALIVE_INTERVAL 秒推一条 ping
# 防止 WPS WebView / 中间代理因连接长时间空闲而强制关闭 WebSocket。
KEEPALIVE_INTERVAL = 20


def _extract_long_term_memory_sync(memory_conversation: dict | None, model: str, provider: str) -> None:
    """Run the entirely synchronous memory extraction pipeline in a worker thread."""
    from app.services.llm_client import create_sync_llm_client
    from app.services.memory import (
        MEMORY_EXTRACT_TEMPERATURE,
        extract_and_save_memory,
        is_long_term_memory_enabled,
    )

    if not is_long_term_memory_enabled():
        logger.info("[WebSocket] 长期记忆开关关闭，跳过自动提取")
        return

    if not (
        isinstance(memory_conversation, dict)
        and str(memory_conversation.get("user", "")).strip()
        and str(memory_conversation.get("assistant", "")).strip()
    ):
        logger.info("[WebSocket] 跳过长期记忆提取：未收到本轮完整 user/assistant 对话")
        return

    conversation = (
        f"USER: {memory_conversation.get('user', '')}\n\nASSISTANT: {memory_conversation.get('assistant', '')}"
    )
    sync_llm = create_sync_llm_client(model, provider, temperature=MEMORY_EXTRACT_TEMPERATURE)
    if sync_llm:
        extract_and_save_memory(conversation, sync_llm)


def _normalize_mode(mode: str | None) -> str:
    """标准化前端传入模式，仅支持单智能体的 agent/ask。"""
    normalized = (mode or "agent").strip().lower()
    if normalized in {"agent", "ask"}:
        return normalized
    return "agent"


def _normalize_document_range(document_range: list | None) -> list | None:
    """Strictly normalize documentRange and require each docId to be int-castable."""
    if document_range is None:
        return None
    if not isinstance(document_range, list):
        raise ValueError("documentRange must be a list")

    normalized: list[dict] = []
    for idx, item in enumerate(document_range):
        if not isinstance(item, dict):
            raise ValueError(f"documentRange[{idx}] must be an object")
        row = dict(item)
        raw_doc_id = row.get("docId")
        if isinstance(raw_doc_id, bool):
            raise ValueError(f"documentRange[{idx}].docId must be int, got bool")
        try:
            row["docId"] = int(raw_doc_id)
        except (TypeError, ValueError):
            raise ValueError(f"documentRange[{idx}].docId must be int, got {raw_doc_id!r}") from None
        normalized.append(row)
    return normalized


# ============== WebSocket 聊天接口 ==============


# These reservations live on the server event loop. No lock is held across
# different windows/sessions; one session's checkpoint must have a single writer.
_active_windows: dict[str, str] = {}
_active_sessions: dict[str, str] = {}
_active_chats: set[str] = set()


class _ChatSocket:
    """Bind outgoing events to a single turn, including tools, errors and done."""

    def __init__(self, websocket, send_lock, chat_id, session_id):
        self.websocket = websocket
        self.app = websocket.app
        self.send_lock = send_lock
        self.chat_id = chat_id
        self.session_id = session_id

    async def send_text(self, payload):
        data = json.loads(payload)
        data.update(chatId=self.chat_id, sessionId=self.session_id)
        async with self.send_lock:
            await self.websocket.send_text(json.dumps(data, ensure_ascii=False))

    async def close(self, **kwargs):
        await self.websocket.close(**kwargs)


@router.websocket("/ws")
async def chat_websocket(websocket: WebSocket):
    """One active turn per window; independent windows run concurrently.

    chatId identifies a turn and its tool responses/stop events. sessionId is
    the persistent conversation/checkpoint. windowId survives reconnects.
    Word clients without explicit IDs use the connection as their window.
    """
    await websocket.accept()
    connection_id = str(uuid.uuid4())
    send_lock = asyncio.Lock()
    stream_task = None
    receive_task = None
    current_socket = None
    scoped_protocol = False
    window_id = None

    async def finish_turn(socket, owner_window, data):
        try:
            await _run_ws_stream(
                socket,
                socket.chat_id,
                data.get("message", ""),
                _normalize_mode(data.get("mode")),
                data.get("model", ""),
                data.get("provider", ""),
                _normalize_document_range(data.get("documentRange")),
                data.get("documentMeta") or {},
                data.get("selectionContext"),
                data.get("files") or [],
                socket.session_id,
                data.get("userResponse"),
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("聊天请求失败 chat_id=%s", socket.chat_id)
            await socket.send_text(json.dumps({"type": "error", "content": str(exc)}, ensure_ascii=False))
            await socket.send_text('{"type":"done"}')
        finally:
            request_stop(socket.chat_id)
            cleanup_tool_request(socket.chat_id)
            _active_chats.discard(socket.chat_id)
            if _active_windows.get(owner_window) == socket.chat_id:
                _active_windows.pop(owner_window)
            if _active_sessions.get(socket.session_id) == socket.chat_id:
                _active_sessions.pop(socket.session_id)

    try:
        while True:
            if receive_task is None:
                receive_task = asyncio.create_task(websocket.receive_text())
            tasks = {receive_task}
            if stream_task is not None:
                tasks.add(stream_task)
            completed, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            if stream_task is not None and stream_task in completed:
                await stream_task
                stream_task = None
                current_socket = None
            if receive_task not in completed:
                continue
            raw = receive_task.result()
            receive_task = None
            try:
                data = json.loads(raw)
            except (json.JSONDecodeError, ValueError):
                continue
            if not isinstance(data, dict):
                continue
            msg_type = data.get("type")
            if msg_type == "chat":
                chat_id = normalize_uuid(data.get("chatId")) or str(uuid.uuid4())
                session_id = normalize_uuid(data.get("sessionId"))
                incoming_window = normalize_uuid(data.get("windowId")) or connection_id
                socket = _ChatSocket(websocket, send_lock, chat_id, session_id)
                error = None
                if any(data.get(key) is not None and normalize_uuid(data[key]) is None
                       for key in ("chatId", "sessionId", "windowId")):
                    error = "chatId、sessionId、windowId 必须是有效 UUID"
                elif window_id is not None and incoming_window != window_id:
                    error = "同一连接不能切换 windowId"
                elif stream_task is not None or incoming_window in _active_windows:
                    error = "当前窗口正在生成，请等待完成或停止后再切换会话"
                elif chat_id in _active_chats:
                    error = "chatId 已在运行，请为每轮请求创建新的 chatId"
                elif session_id is not None and session_id in _active_sessions:
                    error = "此会话正在其他窗口运行，请使用另一个会话"
                if error:
                    await socket.send_text(json.dumps({"type": "error", "content": error}, ensure_ascii=False))
                    await socket.send_text('{"type":"done"}')
                    continue
                window_id = incoming_window
                _active_windows[window_id] = chat_id
                _active_chats.add(chat_id)
                if session_id is not None:
                    _active_sessions[session_id] = chat_id
                create_tool_request(chat_id)
                current_socket = socket
                scoped_protocol = data.get("chatId") is not None
                stream_task = asyncio.create_task(
                    finish_turn(socket, window_id, data), name=f"chat:{chat_id}"
                )
            elif current_socket is not None:
                # A late response/stop from a previous turn cannot affect this one.
                if scoped_protocol and (
                    data.get("chatId") != current_socket.chat_id
                    or data.get("sessionId") != current_socket.session_id
                ):
                    continue
                if msg_type == "stop":
                    request_stop(current_socket.chat_id)
                    stream_task.cancel()
                    with suppress(asyncio.CancelledError):
                        await stream_task
                    await current_socket.send_text('{"type":"done"}')
                    stream_task = None
                    current_socket = None
                elif msg_type in {
                    "document_response", "query_response", "create_document_response",
                    "generate_document_response", "edit_document_response", "delete_response",
                    "insert_break_response",
                }:
                    await submit_tool_response(current_socket.chat_id, data)
                elif msg_type == "frontend_tool_progress":
                    logger.debug("前端工具进度 chat_id=%s %s", current_socket.chat_id, data)
    except WebSocketDisconnect:
        pass
    finally:
        if current_socket is not None:
            request_stop(current_socket.chat_id)
        if stream_task is not None:
            stream_task.cancel()
            with suppress(asyncio.CancelledError, Exception):
                await stream_task
        if receive_task is not None:
            receive_task.cancel()
            with suppress(asyncio.CancelledError, Exception):
                await receive_task


class _IdleAbort(Exception):
    """看门狗主动中止流（达到 IDLE_ABORT_SECONDS）。"""


async def _iterate_with_idle_watchdog(aiter, on_warn, on_abort):
    """
    包装一个异步迭代器，监测 chunk 之间的静默时长：
      - 静默达到 IDLE_WARN_SECONDS 时调用一次 on_warn()
      - 静默达到 IDLE_ABORT_SECONDS 时调用 on_abort() 并以 _IdleAbort 退出
    使用 asyncio.shield 保护底层 __anext__，避免超时取消把 agent 流给搞坏。
    """
    aiterator = aiter.__aiter__()
    next_task: asyncio.Task | None = asyncio.create_task(aiterator.__anext__())
    loop = asyncio.get_event_loop()
    last_chunk_at = loop.time()
    warned = False
    try:
        while True:
            now = loop.time()
            deadline = last_chunk_at + (IDLE_ABORT_SECONDS if warned else IDLE_WARN_SECONDS)
            wait = max(deadline - now, 0.05)

            try:
                item = await asyncio.wait_for(asyncio.shield(next_task), timeout=wait)
            except StopAsyncIteration:
                return
            except asyncio.TimeoutError:
                idle = loop.time() - last_chunk_at
                if not warned and idle >= IDLE_WARN_SECONDS:
                    try:
                        await on_warn()
                    except Exception as cb_err:
                        logger.warning(f"[Watchdog] on_warn 异常: {cb_err}")
                    warned = True
                    continue
                if idle >= IDLE_ABORT_SECONDS:
                    logger.info(f"[Watchdog] ⛔ 已静默 {idle:.0f}s，达到 abort 阈值")
                    next_task.cancel()
                    try:
                        await next_task
                    except BaseException:
                        pass
                    next_task = None
                    try:
                        await on_abort()
                    except Exception as cb_err:
                        logger.error(f"[Watchdog] on_abort 异常: {cb_err}")
                    raise _IdleAbort()
                continue

            yield item
            last_chunk_at = loop.time()
            warned = False
            next_task = asyncio.create_task(aiterator.__anext__())
    finally:
        if next_task is not None and not next_task.done():
            next_task.cancel()
            with suppress(asyncio.CancelledError, StopAsyncIteration):
                await next_task
        await aiterator.aclose()


async def _single_agent_stream_with_state(
    *,
    checkpointer,
    session_id: str | None,
    chat_id: str,
    message: str,
    document_range: list | None,
    document_meta: list | dict | None,
    model: str,
    provider: str,
    mode: str,
    attached_files: list,
    user_response: dict | None = None,
):
    """在同一 thread 锁内运行完整的单智能体流。"""
    async with single_agent_thread_lock(session_id, chat_id):
        config = {"configurable": {"thread_id": build_runtime_thread_id(session_id, chat_id)}}
        interrupts, pending = await load_pending_questions(checkpointer, config)
        if user_response is None and pending:
            # Never append a fresh HumanMessage on top of an unanswered tool call.
            yield f"data: {json.dumps(pending, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
            return
        resume_kwargs = {}
        if user_response is not None:
            resume_kwargs["resume_command"] = answer_command(interrupts, user_response)
            by_id = {item["id"]: item["answer"].strip() for item in user_response["answers"]}
            resume_kwargs["resume_tool_log"] = [
                {"tool": "ask_user", "input": question, "output": by_id[question["id"]], "error": False}
                for question in pending["questions"]
            ]
            saved = await checkpointer.aget_tuple(config)
            original = saved.checkpoint.get("channel_values", {}).get("request_context", {})
            document_range = original.get("document_range", document_range)
            document_meta = original.get("document_meta", document_meta)
            model = original.get("model", model)
            provider = original.get("provider", provider)
            mode = original.get("mode", mode)
        async with aclosing(single_agent_stream(
            message=message,
            document_range=document_range,
            document_meta=document_meta or {},
            model=model,
            provider=provider,
            mode=mode,
            chat_id=chat_id,
            attached_files=attached_files,
            session_id=session_id,
            checkpointer=checkpointer,
            **resume_kwargs,
        )) as stream:
            async for chunk in stream:
                yield chunk


async def _persist_chat_turn(
    *,
    session_id: str | None,
    user_content: str,
    assistant_content: str,
    selection_context: list | dict | None,
    content_parts: list[dict],
    thinking: str | None,
    tool_json: dict | None,
    model: str,
    provider: str | None,
    mode: str,
    attached_files: list[dict] | None,
) -> None:
    """Persist one completed chat turn from backend-owned stream data."""
    if session_id is None:
        logger.info("[WebSocket] 跳过会话保存：缺少 sessionId")
        return

    assistant_text = (assistant_content or "").strip()
    if not assistant_text and not (tool_json or {}).get("calls"):
        logger.info("[WebSocket] 跳过会话保存：assistant 内容和 tool_json 都为空")
        return

    try:
        async with AsyncSessionLocal() as db:
            service = SessionService(db)
            user_msg = await service.add_message(
                session_id=session_id,
                role="user",
                content=user_content or "",
                selection_context=selection_context,
                model=model,
                provider=provider,
                mode=mode,
                attached_files=attached_files,
            )
            if not user_msg:
                await db.rollback()
                logger.error(f"[WebSocket] 会话保存失败：session 不存在 id={session_id}")
                return

            assistant_msg = await service.add_message(
                session_id=session_id,
                role="assistant",
                content=assistant_text,
                tool_json=tool_json or {"calls": []},
                content_parts=content_parts or None,
                thinking=thinking,
                model=model,
                provider=provider,
                mode=mode,
            )
            if not assistant_msg:
                await db.rollback()
                logger.error(f"[WebSocket] assistant 保存失败：session 不存在 id={session_id}")
                return
            await db.commit()
            logger.info(
                f"[WebSocket] 已保存会话消息 session={session_id}, tools={len((tool_json or {}).get('calls', []))}"
            )
    except Exception as e:
        logger.error(f"[WebSocket] 保存会话失败: {e}")
        traceback.print_exc()


async def _run_ws_stream(
    websocket: WebSocket,
    chat_id: str,
    message: str,
    mode: str,
    model: str,
    provider: str,
    document_range: list | None,
    document_meta: list | dict | None,  # 支持单个文档（dict）和多个文档（list）
    selection_context: list | dict | None = None,
    attached_files: list | None = None,
    session_id: str | None = None,
    user_response: dict | None = None,
):
    """在 WebSocket 上运行单智能体流式处理。"""
    mode = _normalize_mode(mode)
    try:
        checkpointer = websocket.app.state.checkpointer
    except AttributeError as exc:
        raise RuntimeError("单智能体 Checkpointer 尚未初始化") from exc

    # 一把锁串行化所有 WebSocket 发送，避免 keepalive / 主流 / watchdog 并发 send
    send_lock = asyncio.Lock()
    content_parts: list[dict] = []
    thinking_parts: list[str] = []
    assistant_text_parts: list[str] = []
    tool_json: dict = {"calls": []}

    def _append_text_part(text: str):
        if not text:
            return
        assistant_text_parts.append(text)
        if content_parts and content_parts[-1].get("type") == "text":
            content_parts[-1]["content"] = str(content_parts[-1].get("content", "")) + text
        else:
            content_parts.append({"type": "text", "content": text})

    def _append_status_part(text: str):
        if text:
            content_parts.append({"type": "status", "content": text})

    def _record_payload(payload: dict):
        ptype = payload.get("type")
        if ptype == "ask_user":
            assistant_text_parts.append("\n".join(item["question"] for item in payload.get("questions", [])))
            content_parts.append({"type": "ask_user", "request": payload})
        elif ptype == "text":
            _append_text_part(str(payload.get("content") or ""))
        elif ptype == "thinking":
            thinking_parts.append(str(payload.get("content") or ""))
        elif ptype == "context_compaction":
            part = {
                "type": "status",
                "content": str(payload.get("content") or ""),
                "contextCompaction": True,
                "loading": payload.get("status") == "started",
            }
            for index in range(len(content_parts) - 1, -1, -1):
                if content_parts[index].get("contextCompaction"):
                    content_parts[index] = part
                    break
            else:
                content_parts.append(part)
        elif ptype in {
            "status",
            "read_document",
            "read_complete",
            "search_document",
            "query_complete",
            "create_document",
            "delete_document",
            "delete_complete",
            "edit_document",
            "edit_complete",
            "insert_break",
            "generate_complete",
        }:
            _append_status_part(str(payload.get("content") or ""))
        elif ptype == "tool_compress":
            content_parts.append({"type": "tool_compress", "content": str(payload.get("content") or "")})
        elif ptype == "mcp_tool_call":
            content_parts.append(
                {
                    "type": "mcp",
                    "toolName": payload.get("toolName") or "unknown_tool",
                    "preview": f"🔧 调用 MCP 工具: {payload.get('toolName') or 'unknown_tool'}",
                    "argsText": json.dumps(payload.get("args") or {}, ensure_ascii=False),
                    "outputText": "",
                    "completed": False,
                    "isError": False,
                }
            )
        elif ptype == "mcp_tool_result":
            tool_name = payload.get("toolName") or "unknown_tool"
            output_text = str(payload.get("outputPreview") or "")
            for part in reversed(content_parts):
                if part.get("type") == "mcp" and part.get("toolName") == tool_name and not part.get("completed"):
                    part["outputText"] = output_text
                    part["completed"] = True
                    part["isError"] = bool(payload.get("isError"))
                    break
            else:
                content_parts.append(
                    {
                        "type": "mcp",
                        "toolName": tool_name,
                        "preview": f"🔧 调用 MCP 工具: {tool_name}",
                        "argsText": "参数未知",
                        "outputText": output_text,
                        "completed": True,
                        "isError": bool(payload.get("isError")),
                    }
                )

    async def _send(payload: str):
        async with send_lock:
            await websocket.send_text(payload)

    for _attempt in range(1):
        try:

            async def _on_idle_warn():
                # 60s 没有 chunk：给前端一个轻提示，避免用户以为卡死
                try:
                    await _send(
                        json.dumps(
                            {"type": "status", "content": "🤔 正在思考下一步"},
                            ensure_ascii=False,
                        )
                    )
                    logger.warning(f"[Watchdog] ⏳ 已静默 {IDLE_WARN_SECONDS}s，已通知前端")
                except Exception:
                    pass

            async def _on_idle_abort():
                # 180s 仍无 chunk：通知 agent 停止 + 告知前端 + 关闭连接
                logger.info(f"[Watchdog] ⛔ 已静默 {IDLE_ABORT_SECONDS}s，停止 agent 并断开 session={chat_id}")
                try:
                    request_stop(chat_id)
                except Exception:
                    pass
                try:
                    await _send(
                        json.dumps(
                            {
                                "type": "status",
                                "content": "⛔ 网络超时连接，自动断开",
                            },
                            ensure_ascii=False,
                        )
                    )
                    await _send(
                        json.dumps(
                            {
                                "type": "error",
                                "content": "⛔ 网络超时连接，自动断开",
                            },
                            ensure_ascii=False,
                        )
                    )
                    await _send(json.dumps({"type": "done"}, ensure_ascii=False))
                except Exception:
                    pass
                try:
                    await websocket.close(code=1011, reason="idle-timeout")
                except Exception:
                    pass

            stream_iter = _single_agent_stream_with_state(
                checkpointer=checkpointer,
                session_id=session_id,
                chat_id=chat_id,
                message=message,
                document_range=document_range,
                document_meta=document_meta,
                model=model,
                provider=provider,
                mode=mode,
                attached_files=attached_files or [],
                user_response=user_response,
            )

            # Keepalive 任务：长 LLM 思考期间（一直没 chunk）也每 KEEPALIVE_INTERVAL
            # 秒发一条 ping，让 WPS WebView / 中间代理看到链路一直有数据，
            # 不会因为"空闲"把 WebSocket 给关掉。前端收到 type=="ping" 直接忽略即可。
            async def _keepalive():
                try:
                    while True:
                        await asyncio.sleep(KEEPALIVE_INTERVAL)
                        try:
                            await _send(json.dumps({"type": "ping"}, ensure_ascii=False))
                        except Exception:
                            return
                except asyncio.CancelledError:
                    return

            keepalive_task = asyncio.create_task(_keepalive())
            memory_conversation: dict | None = None
            token_usage = {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0}

            try:
                async with aclosing(
                    _iterate_with_idle_watchdog(stream_iter, _on_idle_warn, _on_idle_abort)
                ) as chunks:
                    async for chunk in chunks:
                        if chunk.startswith("data: "):
                            payload = chunk[6:].strip()
                            if payload == "[DONE]":
                                # Finish persistence before allowing the client to submit a resume.
                                pass
                            else:
                                try:
                                    parsed_payload = json.loads(payload)
                                    if isinstance(parsed_payload, dict):
                                        _record_payload(parsed_payload)
                                except Exception:
                                    pass
                                await _send(payload)
                        elif chunk.startswith("__token_usage__:"):
                            raw = chunk.split(":", 1)[1].strip()
                            try:
                                parsed = json.loads(raw)
                                if isinstance(parsed, dict):
                                    token_usage = parsed
                            except Exception as e:
                                logger.error(f"[WebSocket] 解析 token usage 失败: {e}")
                        elif chunk.startswith("__memory_conversation__:"):
                            raw = chunk.split(":", 1)[1].strip()
                            try:
                                parsed = json.loads(raw)
                                if isinstance(parsed, dict):
                                    memory_conversation = parsed
                            except Exception as e:
                                logger.error(f"[WebSocket] 解析 memory conversation 失败: {e}")
                        elif chunk.startswith("__tool_json__:"):
                            raw = chunk.split(":", 1)[1].strip()
                            try:
                                parsed = json.loads(raw)
                                if isinstance(parsed, dict):
                                    tool_json = parsed
                            except Exception as e:
                                logger.error(f"[WebSocket] 解析 tool_json 失败: {e}")

                # Completion is sent below, after saving this turn.
            finally:
                keepalive_task.cancel()
                try:
                    await keepalive_task
                except (asyncio.CancelledError, Exception):
                    pass

            # 记忆提取在线程中执行；任务归应用生命周期管理，不阻塞聊天完成。
            memory_tasks = websocket.app.state.memory_tasks

            def memory_done(task: asyncio.Task, tasks=memory_tasks):
                tasks.discard(task)
                if not task.cancelled() and (error := task.exception()) is not None:
                    logger.error(
                        "长期记忆任务 %s 失败: %s",
                        task.get_name(),
                        error,
                        exc_info=(type(error), error, error.__traceback__),
                    )

            memory_task = asyncio.create_task(
                asyncio.to_thread(
                    _extract_long_term_memory_sync,
                    memory_conversation if isinstance(memory_conversation, dict) else None,
                    model,
                    provider,
                ),
                name=f"memory-extract:{chat_id}",
            )
            memory_tasks.add(memory_task)
            memory_task.add_done_callback(memory_done)

            await record_token_usage(
                input_tokens=token_usage.get("input_tokens", 0),
                output_tokens=token_usage.get("output_tokens", 0),
                cached_tokens=token_usage.get("cached_tokens", 0),
            )

            await _persist_chat_turn(
                session_id=session_id,
                user_content=message,
                assistant_content=(
                    str(memory_conversation.get("assistant") or "")
                    if isinstance(memory_conversation, dict)
                    else "".join(assistant_text_parts).strip()
                ),
                selection_context=selection_context if selection_context is not None else document_range,
                content_parts=content_parts,
                thinking="".join(thinking_parts).strip() or None,
                tool_json=tool_json,
                model=model or "auto",
                provider=provider or None,
                mode=mode,
                attached_files=attached_files or None,
            )

            await _send(json.dumps({"type": "done"}, ensure_ascii=False))
            return  # 正常结束
        except _IdleAbort:
            # 看门狗已经处理了通知和 agent 停止，这里直接退出，不重试
            return
        except ContextOverflowError as e:
            logger.error("[WebSocket] 单智能体摘要后上下文仍然超限: %s", e)
            try:
                await _send(
                    json.dumps(
                        {
                            "type": "error",
                            "content": "上下文仍超出模型限制，请新建会话或减少输入内容",
                        },
                        ensure_ascii=False,
                    )
                )
                await _send(json.dumps({"type": "done"}, ensure_ascii=False))
            except Exception:
                pass
            return
        except Exception as e:
            logger.error(f"[WebSocket Stream] 错误: {e}")
            traceback.print_exc()
            try:
                await websocket.send_text(json.dumps({"type": "error", "content": str(e)}, ensure_ascii=False))
                await websocket.send_text(json.dumps({"type": "done"}, ensure_ascii=False))
            except Exception:
                pass
            return
