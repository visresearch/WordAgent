"""Normalize document calls and record their final results."""

from __future__ import annotations

import json
from typing import Any

from langchain.agents.middleware import AgentMiddleware, ToolCallRequest
from langchain_core.messages import ToolMessage
from langgraph.types import Command

from app.services.document_edit_policy import edit_style_context, prepare_document_call
from app.services.tools.tool_log import append_tool_call
from app.services.utils import normalize_tool_args

_BUILTIN_TOOL_NAMES = {
    "ask_user",
    "create_document",
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
            (message for message in result.update.get("messages", []) if isinstance(message, ToolMessage)),
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
            styles, refusal = prepare_document_call(normalized_request.tool_call, normalized_request.state)
            if refusal:
                result = ToolMessage(
                    content=json.dumps(refusal, ensure_ascii=False),
                    tool_call_id=request.tool_call["id"],
                    name=request.tool_call["name"],
                    status="error",
                )
            else:
                token = edit_style_context.set(styles)
                try:
                    result = handler(normalized_request)
                finally:
                    edit_style_context.reset(token)
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
            styles, refusal = prepare_document_call(normalized_request.tool_call, normalized_request.state)
            if refusal:
                result = ToolMessage(
                    content=json.dumps(refusal, ensure_ascii=False),
                    tool_call_id=request.tool_call["id"],
                    name=request.tool_call["name"],
                    status="error",
                )
            else:
                token = edit_style_context.set(styles)
                try:
                    result = await handler(normalized_request)
                finally:
                    edit_style_context.reset(token)
        _record_result(normalized_request, result, agent_name=None, repaired=False)
        return result


TOOL_NORMALIZATION_AND_LOGGING_MIDDLEWARE = ToolNormalizationAndLoggingMiddleware()
