"""单智能体工具基础设施。

设计原则：
- 这里集中放单智能体使用的工具实现。
- 工具 description / 工具 usage 等 markdown 集中在 `tools/prompts/`（`app.services.tools.prompts`），
  `agent/tools.py` 从该包取 `get_tool_description` 装配 `@tool`。
- 回调队列、Pydantic schemas 和 MCP 加载器由单智能体直接复用。
"""

from .callback import (
    _current_chat_id,
    _current_model_name,
    _current_request_context,
    _pending_loops,
    _pending_tool_requests,
    _stop_requested_sessions,
    cleanup_tool_request,
    clear_stop,
    create_tool_request,
    is_stop_requested,
    register_loop,
    request_stop,
    submit_tool_response,
    wait_for_tool_response,
)
from .document_tools import (
    _compact_doc_json,
    _order_document_blocks,
    _delete_document_impl,
    _edit_document_impl,
    _insert_break_impl,
    _create_document_impl,
    _ensure_image_payload_shape,
    _generate_document_impl,
    _read_document_impl,
    _search_document_impl,
    build_delete_document,
    build_edit_document,
    build_insert_break,
    build_create_document,
    build_generate_document,
    build_read_document,
    build_search_document,
)
from .file_tools import build_edit_file, build_list_file, build_read_file
from .mcp_tools import build_mcp_tools_prompt, load_mcp_tools
from .python_tools import build_python_repl
from .schemas import (
    Cell,
    CellParagraph,
    DocumentOutput,
    DocumentQuery,
    Paragraph,
    QueryFilter,
    RangeFilter,
    Run,
    Table,
    TableBlock,
)
from .skill_tools import build_load_skill_context
from .subagent_tools import build_run_sub_agent

__all__ = [
    # callback
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
    "wait_for_tool_response",
    # schemas
    "Cell",
    "CellParagraph",
    "DocumentOutput",
    "DocumentQuery",
    "Paragraph",
    "QueryFilter",
    "RangeFilter",
    "Run",
    "Table",
    "TableBlock",
    # document tools (factories + impls)
    "build_read_document",
    "build_generate_document",
    "build_search_document",
    "build_delete_document",
    "build_edit_document",
    "build_insert_break",
    "build_create_document",
    "build_list_file",
    "build_read_file",
    "build_edit_file",
    "_read_document_impl",
    "_generate_document_impl",
    "_search_document_impl",
    "_delete_document_impl",
    "_edit_document_impl",
    "_insert_break_impl",
    "_create_document_impl",
    "_compact_doc_json",
    "_order_document_blocks",
    "_ensure_image_payload_shape",
    # skill tools
    "build_load_skill_context",
    # MCP tools
    "load_mcp_tools",
    "build_mcp_tools_prompt",
    "build_python_repl",
    # agent-only tools
    "build_run_sub_agent",
]
