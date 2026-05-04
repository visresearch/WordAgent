"""Multi-agent tools package exports."""

from .callback import (
    _current_chat_id,
    _current_model_name,
    _current_request_context,
    create_tool_request,
    cleanup_tool_request,
    register_loop,
    request_stop,
    clear_stop,
    is_stop_requested,
    submit_tool_response,
)

from .document_tools import (
    read_document,
    search_documnet,
    generate_document,
    delete_document,
)

from .agent_tools import (
    create_workflow,
    review_document,
)

from .skill_tools import (
    load_skill_context,
)

from .mcp_tools import (
    load_mcp_tools,
    build_mcp_tools_prompt,
)


# Tools by agent role
PLANNER_TOOLS = [create_workflow]
OUTLINE_TOOLS = [read_document, search_documnet]
WRITER_TOOLS = [read_document, search_documnet, generate_document, delete_document]
REVIEWER_TOOLS = [review_document]

# Research tools: load_skill_context is always available
# MCP tools are loaded dynamically at runtime
RESEARCH_TOOLS = [load_skill_context]

AGENT_TOOLS = {
    "planner": PLANNER_TOOLS,
    "research": RESEARCH_TOOLS,
    "outline": OUTLINE_TOOLS,
    "writer": WRITER_TOOLS,
    "reviewer": REVIEWER_TOOLS,
}

# All tools list (static tools only - MCP tools are loaded dynamically)
ALL_TOOLS = [
    read_document,
    search_documnet,
    generate_document,
    delete_document,
    create_workflow,
    review_document,
    load_skill_context,
]

# Tool map for quick lookup
TOOL_MAP = {t.name: t for t in ALL_TOOLS}


__all__ = [
    # Callbacks
    "_current_chat_id",
    "_current_model_name",
    "_current_request_context",
    "create_tool_request",
    "cleanup_tool_request",
    "register_loop",
    "request_stop",
    "clear_stop",
    "is_stop_requested",
    "submit_tool_response",
    # Document tools
    "read_document",
    "search_documnet",
    "generate_document",
    "delete_document",
    # Agent tools
    "create_workflow",
    "review_document",
    # Skill tools
    "load_skill_context",
    # MCP tools
    "load_mcp_tools",
    "build_mcp_tools_prompt",
    # Collections
    "ALL_TOOLS",
    "AGENT_TOOLS",
    "TOOL_MAP",
    "PLANNER_TOOLS",
    "RESEARCH_TOOLS",
    "OUTLINE_TOOLS",
    "WRITER_TOOLS",
    "REVIEWER_TOOLS",
]
