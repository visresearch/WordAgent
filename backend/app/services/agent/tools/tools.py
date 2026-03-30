"""单智能体工具导出层（兼容旧导入路径）。"""

from .callback import (
    _current_chat_id,
    clear_stop,
    cleanup_tool_request,
    create_tool_request,
    is_stop_requested,
    register_loop,
    request_stop,
    submit_tool_response,
)
from .document_tools import edit_document, read_document, search_documnet
from .skill_tools import load_skill
from .web_tools import web_fetch, web_search

ALL_TOOLS = [read_document, edit_document, search_documnet, web_search, web_fetch, load_skill]
TOOL_MAP = {t.name: t for t in ALL_TOOLS}

__all__ = [
    "ALL_TOOLS",
    "TOOL_MAP",
    "_current_chat_id",
    "clear_stop",
    "cleanup_tool_request",
    "create_tool_request",
    "edit_document",
    "is_stop_requested",
    "load_skill",
    "read_document",
    "register_loop",
    "request_stop",
    "search_documnet",
    "submit_tool_response",
    "web_fetch",
    "web_search",
]
