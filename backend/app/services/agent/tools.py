"""单智能体工具入口。

这是 agent 模式所有工具的**唯一**对外暴露点。所有工具实现都放在共享层
`app.services.tools`，本文件只负责：
1. 用本模式自己的 prompt description 装配出工具实例；
2. 按模式拼装暴露给上层的工具集合 (AGENT_BASE_TOOLS / ASK_BASE_TOOLS)。

外部调用方仍然写 `from app.services.agent.tools import ...`，无需改动。
"""

from __future__ import annotations

from app.services.agent.prompts import get_tool_description
from app.services.tools import (
    # callback
    _current_chat_id,
    _current_model_name,
    _current_request_context,
    _pending_loops,
    _pending_tool_requests,
    _stop_requested_sessions,
    build_delete_document,
    build_edit_file,
    build_generate_document,
    build_list_file,
    build_load_skill_context,
    build_mcp_tools_prompt,
    build_read_file,
    build_read_document,
    build_run_sub_agent,
    build_search_document,
    cleanup_tool_request,
    clear_stop,
    create_tool_request,
    # MCP
    load_mcp_tools,
    # schemas
    DocumentOutput,
    DocumentQuery,
    is_stop_requested,
    register_loop,
    request_stop,
    submit_tool_response,
)


# ---------------------------------------------------------------------------
# 用本模式的 prompt 装配出工具实例
# ---------------------------------------------------------------------------

read_document = build_read_document(get_tool_description("read_document"))
generate_document = build_generate_document(get_tool_description("generate_document"))
search_documnet = build_search_document(get_tool_description("search_document"))
delete_document = build_delete_document(get_tool_description("delete_document"))
load_skill_context = build_load_skill_context(get_tool_description("load_skill_context"))
run_sub_agent = build_run_sub_agent(get_tool_description("run_sub_agent"))
list_file = build_list_file(get_tool_description("list_file"))
read_file = build_read_file(get_tool_description("read_file"))
edit_file = build_edit_file(get_tool_description("edit_file"))


# ---------------------------------------------------------------------------
# 工具集合
# ---------------------------------------------------------------------------

# 基础工具集（不含 MCP 动态工具）
AGENT_BASE_TOOLS = [
    load_skill_context,
    read_document,
    search_documnet,
    generate_document,
    delete_document,
    list_file,
    read_file,
    edit_file,
    run_sub_agent,
]
ASK_BASE_TOOLS = [
    load_skill_context,
    read_document,
    search_documnet,
    run_sub_agent,
]


def get_base_tools_for_mode(mode: str | None) -> list:
    """按模式返回基础工具列表（plan 暂按 agent 处理）。"""
    normalized = (mode or "agent").strip().lower()
    if normalized == "plan":
        normalized = "agent"
    if normalized == "ask":
        return list(ASK_BASE_TOOLS)
    return list(AGENT_BASE_TOOLS)


# 兼容旧引用
BASE_TOOLS = AGENT_BASE_TOOLS
ALL_TOOLS = BASE_TOOLS
TOOL_MAP = {t.name: t for t in BASE_TOOLS}


__all__ = [
    # tools
    "delete_document",
    "edit_file",
    "generate_document",
    "list_file",
    "load_skill_context",
    "read_file",
    "read_document",
    "run_sub_agent",
    "search_documnet",
    # tool sets
    "AGENT_BASE_TOOLS",
    "ASK_BASE_TOOLS",
    "BASE_TOOLS",
    "ALL_TOOLS",
    "TOOL_MAP",
    "get_base_tools_for_mode",
    # callback (re-export)
    "_current_chat_id",
    "_current_model_name",
    "_current_request_context",
    "_pending_loops",
    "_pending_tool_requests",
    "_stop_requested_sessions",
    "cleanup_tool_request",
    "clear_stop",
    "create_tool_request",
    "is_stop_requested",
    "register_loop",
    "request_stop",
    "submit_tool_response",
    # schemas (re-export)
    "DocumentOutput",
    "DocumentQuery",
    # MCP (re-export)
    "load_mcp_tools",
    "build_mcp_tools_prompt",
]
