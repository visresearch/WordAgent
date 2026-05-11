"""多智能体工具入口。

这是 multi-agent 模式所有工具的**唯一**对外暴露点。所有工具实现都放在共享层
`app.services.tools`，本文件只负责：
1. 用本模式自己的 prompt description 装配出工具实例；
2. 按 agent 角色拼装暴露给上层的工具集合
   (PLANNER / OUTLINE / WRITER / REVIEWER / RESEARCH_TOOLS)。

外部调用方仍然写 `from app.services.multi_agent.tools import ...`，无需改动。
"""

from __future__ import annotations

from app.services.tools.prompts import get_tool_description
from app.services.tools import (
    # callback
    _current_chat_id,
    _current_model_name,
    _current_request_context,
    _pending_loops,
    _pending_tool_requests,
    _stop_requested_sessions,
    build_create_workflow,
    build_delete_document,
    build_edit_file,
    build_generate_document,
    build_list_file,
    build_load_skill_context,
    build_mcp_tools_prompt,
    build_read_file,
    build_read_document,
    build_review_document,
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
create_workflow = build_create_workflow(get_tool_description("create_workflow"))
review_document = build_review_document(get_tool_description("review_document"))
list_file = build_list_file(get_tool_description("list_file"))
read_file = build_read_file(get_tool_description("read_file"))
edit_file = build_edit_file(get_tool_description("edit_file"))


# ---------------------------------------------------------------------------
# 角色 → 工具集合
# ---------------------------------------------------------------------------

PLANNER_TOOLS = [create_workflow]
OUTLINE_TOOLS = [read_document, search_documnet]
WRITER_TOOLS = [read_document, search_documnet, generate_document, delete_document]
REVIEWER_TOOLS = [review_document]
# load_skill_context 总是可用；MCP 工具运行时再动态加载
RESEARCH_TOOLS = [load_skill_context, list_file, read_file, edit_file]

AGENT_TOOLS = {
    "planner": PLANNER_TOOLS,
    "research": RESEARCH_TOOLS,
    "outline": OUTLINE_TOOLS,
    "writer": WRITER_TOOLS,
    "reviewer": REVIEWER_TOOLS,
}

# 静态工具列表（不含 MCP 动态工具）
ALL_TOOLS = [
    read_document,
    search_documnet,
    generate_document,
    delete_document,
    create_workflow,
    review_document,
    load_skill_context,
    list_file,
    read_file,
    edit_file,
]
TOOL_MAP = {t.name: t for t in ALL_TOOLS}


__all__ = [
    # tools
    "create_workflow",
    "delete_document",
    "generate_document",
    "list_file",
    "load_skill_context",
    "read_file",
    "edit_file",
    "read_document",
    "review_document",
    "search_documnet",
    # tool sets
    "AGENT_TOOLS",
    "ALL_TOOLS",
    "OUTLINE_TOOLS",
    "PLANNER_TOOLS",
    "RESEARCH_TOOLS",
    "REVIEWER_TOOLS",
    "TOOL_MAP",
    "WRITER_TOOLS",
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
