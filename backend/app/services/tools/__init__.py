"""单 / 多智能体共享的工具基础设施。

设计原则：
- 这里集中放所有工具实现，**包括 agent / multi-agent 各自独有的工具**
  (run_sub_agent / create_workflow / review_document 等)。
- 每个 agent 模式下只有一个 `tools.py` 入口：从这里导入工厂函数，传入
  自家的 prompt description，得到一份装好 LangChain `@tool` 的副本。
- 回调队列 / Pydantic schemas / MCP 加载器 在所有模式间二进制级别相同，
  直接 import。
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
)
from .document_tools import (
    _compact_doc_json,
    _delete_document_impl,
    _ensure_image_payload_shape,
    _generate_document_impl,
    _get_active_doc_id,
    _read_document_impl,
    _search_document_impl,
    build_delete_document,
    build_generate_document,
    build_read_document,
    build_search_document,
)
from .mcp_tools import build_mcp_tools_prompt, load_mcp_tools
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
)
from .skill_tools import build_load_skill_context
from .subagent_tools import build_run_sub_agent
from .workflow_tools import (
    ReviewResult,
    Workflow,
    WorkflowStep,
    build_create_workflow,
    build_review_document,
)

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
    # document tools (factories + impls)
    "build_read_document",
    "build_generate_document",
    "build_search_document",
    "build_delete_document",
    "_read_document_impl",
    "_generate_document_impl",
    "_search_document_impl",
    "_delete_document_impl",
    "_get_active_doc_id",
    "_compact_doc_json",
    "_ensure_image_payload_shape",
    # skill tools
    "build_load_skill_context",
    # MCP tools
    "load_mcp_tools",
    "build_mcp_tools_prompt",
    # agent-only tools
    "build_run_sub_agent",
    # multi-agent-only tools
    "WorkflowStep",
    "Workflow",
    "ReviewResult",
    "build_create_workflow",
    "build_review_document",
]
