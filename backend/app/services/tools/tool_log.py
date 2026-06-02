"""Per-chat tool call capture for persisted conversation history."""

from __future__ import annotations

import contextvars
import json
from typing import Any

_current_tool_log: contextvars.ContextVar[list[dict] | None] = contextvars.ContextVar("_current_tool_log", default=None)


def set_current_tool_log(log: list[dict] | None):
    """Bind the current worker thread to a mutable tool log list."""
    _current_tool_log.set(log)


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (int, float, bool)):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith(("{", "[")):
            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, (dict, list)):
                    return _json_safe(parsed)
            except Exception:
                pass
        return value
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    if hasattr(value, "model_dump"):
        try:
            return _json_safe(value.model_dump())
        except Exception:
            pass
    return str(value)


def append_tool_call(
    *,
    tool: str,
    input: Any = None,
    output: Any = None,
    error: bool = False,
    agent: str | None = None,
    repaired: bool = False,
    is_mcp: bool | None = None,
) -> None:
    """Append one tool invocation to the active per-chat log."""
    log = _current_tool_log.get()
    if log is None:
        return

    item = {
        "tool": tool,
        "input": _json_safe(input),
        "output": _json_safe(output),
        "error": bool(error),
    }
    if agent:
        item["agent"] = agent
    if repaired:
        item["repaired"] = True
    if is_mcp is not None:
        item["is_mcp"] = bool(is_mcp)
    log.append(item)


def build_tool_json(log: list[dict]) -> dict:
    """Return the persisted tool_json payload."""
    return {"calls": _json_safe(log)}
