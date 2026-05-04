"""
Tool callback mechanism for multi-agent tools.
Reuses callback from single-agent.
"""

from app.services.agent.tools.callback import (
    _current_chat_id,
    _current_model_name,
    _current_request_context,
    _pending_loops,
    _pending_tool_requests,
    _stop_requested_sessions,
    is_stop_requested,
    request_stop,
    clear_stop,
    register_loop,
    create_tool_request,
    cleanup_tool_request,
    submit_tool_response,
)

__all__ = [
    "_current_chat_id",
    "_current_model_name",
    "_current_request_context",
    "_pending_loops",
    "_pending_tool_requests",
    "_stop_requested_sessions",
    "is_stop_requested",
    "request_stop",
    "clear_stop",
    "register_loop",
    "create_tool_request",
    "cleanup_tool_request",
    "submit_tool_response",
]
