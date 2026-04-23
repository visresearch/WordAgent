"""单智能体工具导出层（兼容旧导入路径）。"""

from .callback import (
    _current_chat_id,
    _current_model_name,
    _current_request_context,
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
from .skill_tools import list_skills, load_skill_context
from .web_tools import web_fetch

# 基础工具集（不含 MCP 动态工具）
AGENT_BASE_TOOLS = [
    list_skills,
    load_skill_context,
    read_document,
    search_documnet,
    generate_document,
    delete_document,
    run_sub_agent,
    web_fetch,
]
ASK_BASE_TOOLS = [
    list_skills,
    load_skill_context,
    read_document,
    search_documnet,
    run_sub_agent,
    web_fetch,
]


def get_base_tools_for_mode(mode: str | None) -> list:
    """按模式返回基础工具列表（plan 暂按 agent 处理）。"""
    normalized = (mode or "agent").strip().lower()
    if normalized == "plan":
        normalized = "agent"
    if normalized == "ask":
        return list(ASK_BASE_TOOLS)
    return list(AGENT_BASE_TOOLS)


# 兼容旧引用：默认使用 agent 工具集
BASE_TOOLS = AGENT_BASE_TOOLS
# 向后兼容
ALL_TOOLS = BASE_TOOLS
TOOL_MAP = {t.name: t for t in BASE_TOOLS}

__all__ = [
    "ALL_TOOLS",
    "AGENT_BASE_TOOLS",
    "ASK_BASE_TOOLS",
    "BASE_TOOLS",
    "TOOL_MAP",
    "_current_chat_id",
    "_current_request_context",
    "clear_stop",
    "cleanup_tool_request",
    "create_tool_request",
    "delete_document",
    "generate_document",
    "is_stop_requested",
    "get_base_tools_for_mode",
    "read_document",
    "register_loop",
    "request_stop",
    "run_sub_agent",
    "search_documnet",
    "submit_tool_response",
    "list_skills",
    "load_skill_context",
    "web_fetch",
]
