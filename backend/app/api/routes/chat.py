"""
聊天处理路由
"""

import asyncio
import json
import traceback
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

# Idle watchdog 阈值（秒）：超过 IDLE_WARN_SECONDS 没有 chunk 时，
# 给前端一条"正在思考下一步"提示；超过 IDLE_ABORT_SECONDS 仍无 chunk 时，
# 强制停止 LLM 调用并断开 WebSocket。
IDLE_WARN_SECONDS = 60
IDLE_ABORT_SECONDS = 180
# 应用层 keepalive：长 LLM 思考期间，每隔 KEEPALIVE_INTERVAL 秒推一条 ping
# 防止 WPS WebView / 中间代理因连接长时间空闲而强制关闭 WebSocket。
KEEPALIVE_INTERVAL = 20

from app.services.agent.agent import (
    ContextOverflowError,
    process_writing_request_stream as single_agent_stream,
)
from app.services.agent.tools import (
    create_tool_request,
    cleanup_tool_request,
    submit_tool_response,
    request_stop,
    clear_stop,
)
from app.services.multi_agent.agent import (
    process_writing_request_stream as multi_agent_stream,
)
from app.services.multi_agent.tools import (
    create_tool_request as ma_create_tool_request,
    cleanup_tool_request as ma_cleanup_tool_request,
    submit_tool_response as ma_submit_tool_response,
    request_stop as ma_request_stop,
    clear_stop as ma_clear_stop,
)

router = APIRouter()


def _normalize_mode(mode: str | None) -> str:
    """标准化前端传入模式：支持 agent/ask/plan。"""
    normalized = (mode or "agent").strip().lower()
    if normalized in {"agent", "ask", "plan"}:
        return normalized
    return "agent"


# ============== WebSocket 聊天接口 ==============


@router.websocket("/ws")
async def chat_websocket(websocket: WebSocket):
    """
    WebSocket 聊天接口
    支持双向通信：后端可以请求前端执行操作（如获取文档），前端可以回传结果

    使用单一接收者模式避免 concurrent recv 冲突。

    消息协议（JSON）：
    前端 → 后端:
            - {"type": "chat", "message": "...", "mode": "agent|ask|plan", "model": "auto", "documentRange": [...], "documentMeta": {...}, "history": [...]}
      - {"type": "document_response", "documentJson": {...}}
      - {"type": "delete_response", "deletedCount": 3} 或 {"type": "delete_response", "cancelled": true}
      - {"type": "stop"}

    后端 → 前端:
      - {"type": "text", "content": "..."}
      - {"type": "json", "content": {...}}
      - {"type": "status", "content": "..."}
      - {"type": "read_document", "content": "...", "startParaIndex": 0, "endParaIndex": -1}
      - {"type": "delete_document", "content": "...", "startParaIndex": 0, "endParaIndex": -1}
      - {"type": "done"}
      - {"type": "error", "content": "..."}
    """
    await websocket.accept()
    chat_id = str(uuid.uuid4())
    print(f"[WebSocket] 连接建立 session={chat_id}")

    # 为此会话创建工具回调队列（单智能体 + 多智能体）
    create_tool_request(chat_id)
    ma_create_tool_request(chat_id)

    # 跟踪当前请求使用的模式（决定 tool 回调转发目标）
    active_mode: str = "agent"

    # 单一接收者：所有 WebSocket 消息通过此队列分发
    # 避免多个协程同时调用 websocket.receive_text() 导致 RuntimeError
    msg_queue: asyncio.Queue = asyncio.Queue()

    async def _receiver():
        """专用 WebSocket 接收协程 - 只有这一个协程调用 recv"""
        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    await msg_queue.put(json.loads(raw))
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"[WebSocket] ⚠️ JSON 解析失败，跳过此消息: {e}")
                    continue
        except WebSocketDisconnect:
            await msg_queue.put(None)
        except Exception as e:
            print(f"[WebSocket] ⚠️ 接收协程异常: {e}")
            await msg_queue.put(None)

    recv_task = asyncio.create_task(_receiver())

    try:
        while True:
            # 从消息队列获取下一条消息
            data = await msg_queue.get()
            if data is None:
                # 连接已断开
                break

            msg_type = data.get("type", "")

            if msg_type == "chat":
                # 新请求开始前，清理上一次 stop 状态并重建工具队列（丢弃残留消息）
                clear_stop(chat_id)
                create_tool_request(chat_id)
                ma_clear_stop(chat_id)
                ma_create_tool_request(chat_id)

                # 聊天请求
                message = data.get("message", "")
                mode = _normalize_mode(data.get("mode", "agent"))
                active_mode = mode  # 记录当前活跃模式，用于后续 tool 回调转发
                model = data.get("model", "")
                provider = data.get("provider", "")
                document_range = data.get("documentRange")
                document_meta = data.get("documentMeta") or {}
                history = data.get("history", [])
                attached_files = data.get("files", [])  # 附件列表 [{file_id, filename, content_type, is_image}, ...]
                enable_thinking = data.get("enableThinking", True)  # 是否启用深度思考

                print("=" * 50)
                print("收到 WebSocket 聊天请求:")
                print(f"用户消息: {message}")
                print(f"模式: {mode}")
                print(f"模型: {model}")
                print(f"深度思考: {enable_thinking}")
                if document_range:
                    print(f"文档范围: {document_range}")
                if document_meta:
                    # 支持单个文档和多个文档的打印
                    if isinstance(document_meta, list):
                        print(f"文档元信息: {document_meta}")
                    else:
                        print(
                            "文档元信息:",
                            {
                                "documentName": document_meta.get("documentName", ""),
                                "totalParas": document_meta.get("totalParas", 0),
                                "isEmpty": document_meta.get("isEmpty", False),
                            },
                        )
                if attached_files:
                    print(f"附件: {[f.get('filename', '?') for f in attached_files]}")
                print("=" * 50)

                # 启动流式处理
                stream_task = asyncio.create_task(
                    _run_ws_stream(
                        websocket,
                        chat_id,
                        message,
                        mode,
                        model,
                        provider,
                        document_range,
                        document_meta,
                        history,
                        attached_files,
                        enable_thinking,
                    )
                )

                # 在流式生成期间，继续从队列读取消息（document_response / stop）
                while not stream_task.done():
                    try:
                        incoming = await asyncio.wait_for(msg_queue.get(), timeout=0.5)
                        if incoming is None:
                            # 连接断开 - 必须通知 agent 线程停止，
                            # 否则 ThreadPoolExecutor 里的 LangGraph 会变成孤儿继续跑
                            print(f"[WebSocket] 客户端断开，停止 agent (session={chat_id})")
                            request_stop(chat_id)
                            ma_request_stop(chat_id)
                            stream_task.cancel()
                            try:
                                await stream_task
                            except asyncio.CancelledError:
                                pass
                            return
                        incoming_type = incoming.get("type", "")
                        if incoming_type == "document_response":
                            print(f"[WebSocket] 收到前端回传文档")
                            if active_mode == "plan":
                                await ma_submit_tool_response(chat_id, incoming)
                            else:
                                await submit_tool_response(chat_id, incoming)
                        elif incoming_type == "query_response":
                            print(f"[WebSocket] 收到前端回传查询结果")
                            if active_mode == "plan":
                                await ma_submit_tool_response(chat_id, incoming)
                            else:
                                await submit_tool_response(chat_id, incoming)
                        elif incoming_type == "delete_response":
                            # delete_document 为非阻塞工具，不再等待前端回传，仅记录日志
                            print(f"[WebSocket] 收到前端删除结果（仅记录）: {incoming}")
                        elif incoming_type == "stop":
                            print(f"[WebSocket] 收到停止请求")
                            request_stop(chat_id)
                            ma_request_stop(chat_id)
                            stream_task.cancel()
                            try:
                                await stream_task
                            except asyncio.CancelledError:
                                pass
                            await websocket.send_text(json.dumps({"type": "done"}, ensure_ascii=False))
                            break
                    except asyncio.TimeoutError:
                        continue

                # 确保 stream_task 完成
                if not stream_task.done():
                    try:
                        await stream_task
                    except asyncio.CancelledError:
                        pass

            elif msg_type == "document_response":
                # 非流式过程中的文档回传（fallback）
                if active_mode == "plan":
                    await ma_submit_tool_response(chat_id, data)
                else:
                    await submit_tool_response(chat_id, data)

            elif msg_type == "query_response":
                # 非流式过程中的查询结果回传（fallback）
                if active_mode == "plan":
                    await ma_submit_tool_response(chat_id, data)
                else:
                    await submit_tool_response(chat_id, data)

            elif msg_type == "stop":
                print(f"[WebSocket] 收到停止请求(空闲态)")
                request_stop(chat_id)
                ma_request_stop(chat_id)

    except WebSocketDisconnect:
        print(f"[WebSocket] 连接断开 session={chat_id}")
    except Exception as e:
        print(f"[WebSocket] 错误: {e}")
        import traceback

        traceback.print_exc()
        try:
            await websocket.send_text(json.dumps({"type": "error", "content": str(e)}, ensure_ascii=False))
        except Exception:
            pass
    finally:
        # 兜底：确保 agent 线程拿到停止信号，避免孤儿继续跑 LLM/工具
        try:
            request_stop(chat_id)
            ma_request_stop(chat_id)
        except Exception:
            pass
        recv_task.cancel()
        cleanup_tool_request(chat_id)
        ma_cleanup_tool_request(chat_id)
        print(f"[WebSocket] 清理完成 session={chat_id}")


from app.services.agent.agent import ContextOverflowError


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
                        print(f"[Watchdog] on_warn 异常: {cb_err}")
                    warned = True
                    continue
                if idle >= IDLE_ABORT_SECONDS:
                    print(f"[Watchdog] ⛔ 已静默 {idle:.0f}s，达到 abort 阈值")
                    next_task.cancel()
                    try:
                        await next_task
                    except BaseException:
                        pass
                    next_task = None
                    try:
                        await on_abort()
                    except Exception as cb_err:
                        print(f"[Watchdog] on_abort 异常: {cb_err}")
                    raise _IdleAbort()
                continue

            yield item
            last_chunk_at = loop.time()
            warned = False
            next_task = asyncio.create_task(aiterator.__anext__())
    finally:
        if next_task is not None and not next_task.done():
            next_task.cancel()


async def _run_ws_stream(
    websocket: WebSocket,
    chat_id: str,
    message: str,
    mode: str,
    model: str,
    provider: str,
    document_range: list | None,
    document_meta: list | dict | None,  # 支持单个文档（dict）和多个文档（list）
    history: list,
    attached_files: list | None = None,
    enable_thinking: bool = True,
):
    """在 WebSocket 上运行流式处理，支持上下文超限时自动重试"""
    mode = _normalize_mode(mode)
    stream_fn = multi_agent_stream if mode == "plan" else single_agent_stream

    # 一把锁串行化所有 WebSocket 发送，避免 keepalive / 主流 / watchdog 并发 send
    send_lock = asyncio.Lock()

    async def _send(payload: str):
        async with send_lock:
            await websocket.send_text(payload)

    max_retries = 2
    for attempt in range(max_retries):
        try:
            _done_sent = False

            async def _on_idle_warn():
                # 60s 没有 chunk：给前端一个轻提示，避免用户以为卡死
                try:
                    await _send(
                        json.dumps(
                            {"type": "status", "content": "🤔 正在思考下一步"},
                            ensure_ascii=False,
                        )
                    )
                    print(f"[Watchdog] ⏳ 已静默 {IDLE_WARN_SECONDS}s，已通知前端")
                except Exception:
                    pass

            async def _on_idle_abort():
                # 180s 仍无 chunk：通知 agent 停止 + 告知前端 + 关闭连接
                print(f"[Watchdog] ⛔ 已静默 {IDLE_ABORT_SECONDS}s，停止 agent 并断开 session={chat_id}")
                try:
                    request_stop(chat_id)
                    ma_request_stop(chat_id)
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

            stream_iter = stream_fn(
                message=message,
                document_range=document_range,
                document_meta=document_meta or {},
                history=history,
                model=model,
                provider=provider,
                mode=mode,
                chat_id=chat_id,
                attached_files=attached_files or [],
                enable_thinking=enable_thinking,
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

            try:
                async for chunk in _iterate_with_idle_watchdog(stream_iter, _on_idle_warn, _on_idle_abort):
                    if chunk.startswith("data: "):
                        payload = chunk[6:].strip()
                        if payload == "[DONE]":
                            if not _done_sent:
                                await _send(json.dumps({"type": "done"}, ensure_ascii=False))
                                _done_sent = True
                        else:
                            await _send(payload)
                    elif chunk.startswith("__memory_conversation__:"):
                        raw = chunk.split(":", 1)[1].strip()
                        try:
                            parsed = json.loads(raw)
                            if isinstance(parsed, dict):
                                memory_conversation = parsed
                        except Exception as e:
                            print(f"[WebSocket] 解析 memory conversation 失败: {e}")

                # 确保发送一次 done（防止 agent 异常时未发送）
                if not _done_sent:
                    await _send(json.dumps({"type": "done"}, ensure_ascii=False))
            finally:
                keepalive_task.cancel()
                try:
                    await keepalive_task
                except (asyncio.CancelledError, Exception):
                    pass

            # 异步提取长期记忆（不阻塞前端）
            async def _extract_memory_async():
                try:
                    from app.services.memory import extract_and_save_memory, MEMORY_EXTRACT_TEMPERATURE
                    from app.services.llm_client import create_sync_llm_client

                    # 仅使用本次对话结束后回传的 user/assistant 对，禁止回退到历史记录。
                    if not (
                        isinstance(memory_conversation, dict)
                        and str(memory_conversation.get("user", "")).strip()
                        and str(memory_conversation.get("assistant", "")).strip()
                    ):
                        print("[WebSocket] 跳过长期记忆提取：未收到本轮完整 user/assistant 对话")
                        return

                    conversation = (
                        f"USER: {memory_conversation.get('user', '')}\n\n"
                        f"ASSISTANT: {memory_conversation.get('assistant', '')}"
                    )

                    sync_llm = create_sync_llm_client(model, provider, temperature=MEMORY_EXTRACT_TEMPERATURE)
                    if sync_llm:
                        extract_and_save_memory(conversation, sync_llm)
                except Exception as e:
                    print(f"[WebSocket] 长期记忆提取失败: {e}")

            # 创建后台任务执行记忆提取，不等待完成
            asyncio.create_task(_extract_memory_async())

            return  # 正常结束
        except _IdleAbort:
            # 看门狗已经处理了通知和 agent 停止，这里直接退出，不重试
            return
        except ContextOverflowError as e:
            print(
                f"[WebSocket] 上下文超限，尝试重试（{attempt + 1}/{max_retries}），压缩后 {len(e.compressed_history)} 条历史"
            )
            history = e.compressed_history  # 更新 history，用压缩后的历史重试
            # 发一条前端通知
            try:
                await websocket.send_text(
                    json.dumps({"type": "status", "content": "🗜️ 上下文压缩完成，正在重试…"}, ensure_ascii=False)
                )
            except Exception:
                pass
            continue
        except Exception as e:
            print(f"[WebSocket Stream] 错误: {e}")
            traceback.print_exc()
            try:
                await websocket.send_text(json.dumps({"type": "error", "content": str(e)}, ensure_ascii=False))
                await websocket.send_text(json.dumps({"type": "done"}, ensure_ascii=False))
            except Exception:
                pass
            return
