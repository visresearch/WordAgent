"""单智能体工具导出层（兼容旧导入路径）。"""

from .callback import (
    _current_chat_id,
    _current_model_name,
    clear_stop,
    cleanup_tool_request,
    create_tool_request,
    is_stop_requested,
    register_loop,
    request_stop,
    submit_tool_response,
)
from .document_tools import delete_document, generate_document, read_document, search_documnet
from .runSubAgent_tools import run_sub_agent
from .web_tools import web_fetch

# 基础工具集（不含 MCP 动态工具）
BASE_TOOLS = [read_document, search_documnet, generate_document, delete_document, run_sub_agent]
# 向后兼容
ALL_TOOLS = BASE_TOOLS
TOOL_MAP = {t.name: t for t in BASE_TOOLS}

__all__ = [
    "ALL_TOOLS",
    "BASE_TOOLS",
    "TOOL_MAP",
    "_current_chat_id",
    "clear_stop",
    "cleanup_tool_request",
    "create_tool_request",
    "delete_document",
    "generate_document",
    "is_stop_requested",
    "read_document",
    "register_loop",
    "request_stop",
    "run_sub_agent",
    "search_documnet",
    "submit_tool_response",
    "web_fetch",
]
