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
from .web_tools import web_fetch, web_search

# 主 Agent 工具集：read_document / search_documnet / run_sub_agent
# 文档写入、删除、网络搜索等能力已委托给子智能体（通过 run_sub_agent 调用）
ALL_TOOLS = [read_document, search_documnet, run_sub_agent]
TOOL_MAP = {t.name: t for t in ALL_TOOLS}

__all__ = [
    "ALL_TOOLS",
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
    "web_search",
]
