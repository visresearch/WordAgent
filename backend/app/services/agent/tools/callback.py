"""工具回调等待机制（WebSocket 工具回传队列）。"""

import asyncio
import contextvars

# 存储每个会话的等待队列：{chat_id: asyncio.Queue}
_pending_tool_requests: dict[str, asyncio.Queue] = {}
# 存储每个会话的事件循环引用（供 tool 在同步线程中回到异步）
_pending_loops: dict[str, asyncio.AbstractEventLoop] = {}
# 存储每个会话的停止状态（用户点击停止后置为 True）
_stop_requested_sessions: set[str] = set()
# 当前线程使用的 chat_id（通过 contextvars 传递到 tool 函数中）
_current_chat_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("_current_chat_id", default=None)
# 当前线程使用的模型名（供子智能体继承主智能体的模型）
_current_model_name: contextvars.ContextVar[str | None] = contextvars.ContextVar("_current_model_name", default=None)
# 当前线程请求上下文（供工具获取文档元信息/范围等）
_current_request_context: contextvars.ContextVar[dict | None] = contextvars.ContextVar(
    "_current_request_context", default=None
)


def create_tool_request(chat_id: str) -> asyncio.Queue:
    """为一个会话创建等待队列。"""
    q = asyncio.Queue()
    _pending_tool_requests[chat_id] = q
    _stop_requested_sessions.discard(chat_id)
    return q


def register_loop(chat_id: str, loop: asyncio.AbstractEventLoop):
    """注册会话使用的事件循环（供 tool 函数中跨线程调用）。"""
    _pending_loops[chat_id] = loop


def cleanup_tool_request(chat_id: str):
    """清理会话的等待队列。"""
    _pending_tool_requests.pop(chat_id, None)
    _pending_loops.pop(chat_id, None)
    _stop_requested_sessions.discard(chat_id)


def request_stop(chat_id: str):
    """标记会话停止，并唤醒可能正在等待前端回传的工具调用。"""
    _stop_requested_sessions.add(chat_id)
    q = _pending_tool_requests.get(chat_id)
    loop = _pending_loops.get(chat_id)
    if q and loop:
        try:
            asyncio.run_coroutine_threadsafe(q.put({"type": "stop", "error": "stopped_by_user"}), loop)
        except Exception:
            pass


def clear_stop(chat_id: str):
    """清除会话停止标记（用于下一次新请求）。"""
    _stop_requested_sessions.discard(chat_id)


def is_stop_requested(chat_id: str | None) -> bool:
    """判断会话是否收到停止请求。"""
    return bool(chat_id) and chat_id in _stop_requested_sessions


async def submit_tool_response(chat_id: str, data: dict):
    """前端通过 WebSocket 回传工具结果时调用。"""
    if is_stop_requested(chat_id):
        # 停止后忽略迟到的工具回包，避免再次唤醒 agent 流程
        print(f"[ToolCallback] ⛔ 忽略回传（已停止）session={chat_id}")
        return
    q = _pending_tool_requests.get(chat_id)
    if q:
        data_type = data.get("type", "?") if isinstance(data, dict) else type(data).__name__
        print(f"[ToolCallback] ✅ 放入队列 session={chat_id}, type={data_type}, 队列大小={q.qsize() + 1}")
        await q.put(data)
    else:
        print(f"[ToolCallback] ⚠️ 找不到 session {chat_id} 的等待队列")
