"""Retry read tools without replaying uncertain document mutations."""

from __future__ import annotations

import json

from langchain.agents.middleware import ToolRetryMiddleware
from langchain_core.messages import ToolMessage

from app.services.utils import _get_env_float, _get_env_int

_DOCUMENT_MUTATIONS = {"edit_document", "delete_document", "generate_document", "insert_break"}
TOOL_MAX_RETRIES = _get_env_int("WORDAGENT_TOOL_MAX_RETRIES", 2)
TOOL_RETRY_ON_FAILURE = "continue"
TOOL_RETRY_BACKOFF_FACTOR = _get_env_float("WORDAGENT_TOOL_RETRY_BACKOFF_FACTOR", 2.0)
TOOL_RETRY_INITIAL_DELAY = _get_env_float("WORDAGENT_TOOL_RETRY_INITIAL_DELAY", 1.0)
TOOL_RETRY_MAX_DELAY = _get_env_float("WORDAGENT_TOOL_RETRY_MAX_DELAY", 10.0)
TOOL_RETRY_JITTER = True


class MutationSafeToolRetryMiddleware(ToolRetryMiddleware):
    """Read tools may retry; a write exception requires inspection, never replay."""

    @staticmethod
    def _uncertain(request, exc):
        return ToolMessage(
            content=json.dumps(
                {
                    "success": None,
                    "requiresRead": True,
                    "retryable": False,
                    "error": f"写操作异常，未自动重试；请读取目标区域确认实际状态：{exc}",
                },
                ensure_ascii=False,
            ),
            tool_call_id=request.tool_call["id"],
            name=request.tool_call["name"],
            status="error",
        )

    def wrap_tool_call(self, request, handler):
        if request.tool_call["name"] not in _DOCUMENT_MUTATIONS:
            return super().wrap_tool_call(request, handler)
        try:
            return handler(request)
        except Exception as exc:
            return self._uncertain(request, exc)

    async def awrap_tool_call(self, request, handler):
        if request.tool_call["name"] not in _DOCUMENT_MUTATIONS:
            return await super().awrap_tool_call(request, handler)
        try:
            return await handler(request)
        except Exception as exc:
            return self._uncertain(request, exc)


# max_retries applies only to non-mutating tools.
TOOL_RETRY_MIDDLEWARE = MutationSafeToolRetryMiddleware(
    max_retries=TOOL_MAX_RETRIES,
    on_failure=TOOL_RETRY_ON_FAILURE,
    backoff_factor=TOOL_RETRY_BACKOFF_FACTOR,
    initial_delay=TOOL_RETRY_INITIAL_DELAY,
    max_delay=TOOL_RETRY_MAX_DELAY,
    jitter=TOOL_RETRY_JITTER,
)
