"""
聊天处理路由
"""

import asyncio
import json
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.agent.agent import (
    process_writing_request_stream as single_agent_stream,
)
from app.services.multi_agent.agent import (
    process_writing_request_stream as multi_agent_stream,
)
from app.services.agent.tools.tools import (
    create_tool_request,
    cleanup_tool_request,
    submit_tool_response,
    request_stop,
    clear_stop,
)
from app.services.multi_agent.tools import (
    create_tool_request as ma_create_tool_request,
    cleanup_tool_request as ma_cleanup_tool_request,
    submit_tool_response as ma_submit_tool_response,
    request_stop as ma_request_stop,
    clear_stop as ma_clear_stop,
)

router = APIRouter()


# ============== WebSocket 聊天接口 ==============


@router.websocket("/ws")
async def chat_websocket(websocket: WebSocket):
    """
    WebSocket 聊天接口
    支持双向通信：后端可以请求前端执行操作（如获取文档），前端可以回传结果

    使用单一接收者模式避免 concurrent recv 冲突。

    消息协议（JSON）：
    前端 → 后端:
      - {"type": "chat", "message": "...", "mode": "agent", "model": "auto", "documentRange": [...], "documentMeta": {...}, "history": [...]}
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

    # 为此会话创建工具回调队列（两套 agent 各自维护独立队列）
    create_tool_request(chat_id)
    ma_create_tool_request(chat_id)

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
                ma_clear_stop(chat_id)
                create_tool_request(chat_id)
                ma_create_tool_request(chat_id)

                # 聊天请求
                message = data.get("message", "")
                mode = data.get("mode", "agent")  # 默认 agent 模式（单智能体）
                model = data.get("model", "auto")
                document_range = data.get("documentRange")
                document_meta = data.get("documentMeta") or {}
                history = data.get("history", [])
                attached_files = data.get("files", [])  # 附件列表 [{file_id, filename, content_type, is_image}, ...]

                print("=" * 50)
                print("收到 WebSocket 聊天请求:")
                print(f"用户消息: {message}")
                print(f"模式: {mode}")
                print(f"模型: {model}")
                if document_range:
                    print(f"文档范围: {document_range}")
                if document_meta:
                    print(
                        "文档元信息:",
                        {
                            "documentName": document_meta.get("documentName", ""),
                            "totalParas": document_meta.get("totalParas", 0),
                            "parsedAt": document_meta.get("parsedAt", ""),
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
                        document_range,
                        document_meta,
                        history,
                        attached_files,
                    )
                )

                # 在流式生成期间，继续从队列读取消息（document_response / stop）
                while not stream_task.done():
                    try:
                        incoming = await asyncio.wait_for(msg_queue.get(), timeout=0.5)
                        if incoming is None:
                            # 连接断开
                            stream_task.cancel()
                            try:
                                await stream_task
                            except asyncio.CancelledError:
                                pass
                            return
                        incoming_type = incoming.get("type", "")
                        if incoming_type == "document_response":
                            print(f"[WebSocket] 收到前端回传文档")
                            await submit_tool_response(chat_id, incoming)
                            await ma_submit_tool_response(chat_id, incoming)
                        elif incoming_type == "query_response":
                            print(f"[WebSocket] 收到前端回传查询结果")
                            await submit_tool_response(chat_id, incoming)
                            await ma_submit_tool_response(chat_id, incoming)
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
                await submit_tool_response(chat_id, data)

            elif msg_type == "query_response":
                # 非流式过程中的查询结果回传（fallback）
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
        recv_task.cancel()
        cleanup_tool_request(chat_id)
        ma_cleanup_tool_request(chat_id)
        print(f"[WebSocket] 清理完成 session={chat_id}")


async def _run_ws_stream(
    websocket: WebSocket,
    chat_id: str,
    message: str,
    mode: str,
    model: str,
    document_range: list | None,
    document_meta: dict | None,
    history: list,
    attached_files: list | None = None,
):
    """在 WebSocket 上运行流式处理"""
    try:
        # 根据模式选择 agent：agent 模式走多智能体，其他走单 agent
        stream_fn = multi_agent_stream if mode == "plan" else single_agent_stream
        async for chunk in stream_fn(
            message=message,
            document_range=document_range,
            document_meta=document_meta or {},
            history=history,
            model=model,
            mode=mode,
            chat_id=chat_id,
            attached_files=attached_files or [],
        ):
            # chunk 格式: "data: {...}\n\n" 或 "data: [DONE]\n\n"
            # 解析 SSE 格式，转为 WebSocket JSON
            if chunk.startswith("data: "):
                payload = chunk[6:].strip()
                if payload == "[DONE]":
                    await websocket.send_text(json.dumps({"type": "done"}, ensure_ascii=False))
                else:
                    # 直接转发 JSON 数据
                    await websocket.send_text(payload)
    except Exception as e:
        print(f"[WebSocket Stream] 错误: {e}")
        import traceback

        traceback.print_exc()
        try:
            await websocket.send_text(json.dumps({"type": "error", "content": str(e)}, ensure_ascii=False))
            await websocket.send_text(json.dumps({"type": "done"}, ensure_ascii=False))
        except Exception:
            pass
