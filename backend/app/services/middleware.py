"""LangChain middleware used by WordAgent's single-agent mode."""

from __future__ import annotations

from typing import Any

from langchain.agents.middleware import (
    AgentMiddleware,
    ModelCallLimitMiddleware,
    ModelRequest,
    TodoListMiddleware,
    ToolCallRequest,
    ToolRetryMiddleware,
)
from langchain_core.messages import ToolMessage
from langgraph.types import Command

from app.services.tools.tool_log import append_tool_call
from app.services.utils import normalize_tool_args

# Agent middleware configuration
MODEL_CALL_RUN_LIMIT = 100
MODEL_CALL_LIMIT_EXIT_BEHAVIOR = "end"
TOOL_MAX_RETRIES = 2
TOOL_RETRY_ON_FAILURE = "continue"
TOOL_RETRY_BACKOFF_FACTOR = 2.0
TOOL_RETRY_INITIAL_DELAY = 1.0
TOOL_RETRY_MAX_DELAY = 10.0
TOOL_RETRY_JITTER = True

_BUILTIN_TOOL_NAMES = {
    "create_document",
    "create_workflow",
    "delete_document",
    "edit_document",
    "edit_file",
    "generate_document",
    "insert_break",
    "list_file",
    "load_skill_context",
    "python_repl",
    "read_document",
    "read_file",
    "review_document",
    "run_sub_agent",
    "search_document",
    "write_todos",
}


def _is_mcp_tool(tool_name: str) -> bool:
    return tool_name.startswith("mcp_") or tool_name not in _BUILTIN_TOOL_NAMES


def _normalized_request(request: ToolCallRequest) -> ToolCallRequest:
    """Apply WordAgent's argument normalization before every tool attempt."""
    tool_call = request.tool_call
    normalized_args = normalize_tool_args(tool_call["name"], tool_call.get("args", {}))
    return request.override(tool_call={**tool_call, "args": normalized_args})


def _record_result(
    request: ToolCallRequest,
    result: ToolMessage | Command[Any],
    *,
    agent_name: str | None,
    repaired: bool,
) -> None:
    tool_message = result if isinstance(result, ToolMessage) else None
    if isinstance(result, Command) and isinstance(result.update, dict):
        tool_message = next(
            (
                message
                for message in result.update.get("messages", [])
                if isinstance(message, ToolMessage)
            ),
            None,
        )
    if tool_message is None:
        return

    append_tool_call(
        tool=request.tool_call["name"],
        input=request.tool_call.get("args", {}),
        output=tool_message.content,
        error=tool_message.status == "error",
        agent=agent_name,
        repaired=repaired,
        is_mcp=_is_mcp_tool(request.tool_call["name"]),
    )


# region MIDDLEWARE CLASSES

class ToolResultCompactionMiddleware(AgentMiddleware):
    """Compact old tool results for model input without mutating agent history."""

    @staticmethod
    def _compact(request: ModelRequest) -> ModelRequest:
        try:
            from app.services.context import _light_compact_tool_results

            messages, meta = _light_compact_tool_results(request.messages)
            if meta.get("light_compact_triggered"):
                return request.override(messages=messages)
        except Exception:
            pass
        return request

    def wrap_model_call(self, request: ModelRequest, handler):
        return handler(self._compact(request))

    async def awrap_model_call(self, request: ModelRequest, handler):
        return await handler(self._compact(request))


class ToolNormalizationAndLoggingMiddleware(AgentMiddleware):
    """Normalize tool arguments and persist the final tool result."""

    def wrap_tool_call(self, request: ToolCallRequest, handler):
        try:
            normalized_request = _normalized_request(request)
        except Exception as exc:
            result = ToolMessage(
                content=f"Tool '{request.tool_call['name']}' argument normalization failed: {exc}",
                tool_call_id=request.tool_call.get("id"),
                name=request.tool_call["name"],
                status="error",
            )
            normalized_request = request
        else:
            result = handler(normalized_request)
        _record_result(normalized_request, result, agent_name=None, repaired=False)
        return result

    async def awrap_tool_call(self, request: ToolCallRequest, handler):
        try:
            normalized_request = _normalized_request(request)
        except Exception as exc:
            result = ToolMessage(
                content=f"Tool '{request.tool_call['name']}' argument normalization failed: {exc}",
                tool_call_id=request.tool_call.get("id"),
                name=request.tool_call["name"],
                status="error",
            )
            normalized_request = request
        else:
            result = await handler(normalized_request)
        _record_result(normalized_request, result, agent_name=None, repaired=False)
        return result


TODO_LIST_MIDDLEWARE = TodoListMiddleware()

MODEL_CALL_LIMIT_MIDDLEWARE = ModelCallLimitMiddleware(
    run_limit=MODEL_CALL_RUN_LIMIT,
    exit_behavior=MODEL_CALL_LIMIT_EXIT_BEHAVIOR,
)

TOOL_RESULT_COMPACTION_MIDDLEWARE = ToolResultCompactionMiddleware()

TOOL_NORMALIZATION_AND_LOGGING_MIDDLEWARE = ToolNormalizationAndLoggingMiddleware()

# max_retries excludes the first attempt, so a tool runs at most three times.
TOOL_RETRY_MIDDLEWARE = ToolRetryMiddleware(
    max_retries=TOOL_MAX_RETRIES,
    on_failure=TOOL_RETRY_ON_FAILURE,
    backoff_factor=TOOL_RETRY_BACKOFF_FACTOR,
    initial_delay=TOOL_RETRY_INITIAL_DELAY,
    max_delay=TOOL_RETRY_MAX_DELAY,
    jitter=TOOL_RETRY_JITTER,
)

DEFAULT_AGENT_MIDDLEWARE = [
    TODO_LIST_MIDDLEWARE,
    MODEL_CALL_LIMIT_MIDDLEWARE,
    TOOL_RESULT_COMPACTION_MIDDLEWARE,
    TOOL_NORMALIZATION_AND_LOGGING_MIDDLEWARE,
    TOOL_RETRY_MIDDLEWARE,
]
