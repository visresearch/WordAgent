"""
langchain 中间件
1. NotifyingSummarizationMiddleware
    上下文摘要中间件：在模型调用前对历史消息进行摘要，减少 token 消耗。

2. ToolResultCompressionMiddleware
    工具结果压缩中间件：在模型调用前对历史工具调用结果进行压缩，减少 token 消耗。

3. ToolNormalizationAndLoggingMiddleware
    工具调用参数归一化和结果持久化中间件：在每次工具调用前对参数进行归一化，并在工具调用后将最终结果持久化到数据库。

4. ToolRetryMiddleware
    工具调用重试中间件：在工具调用失败时进行重试

5. ModelCallLimitMiddleware
    模型调用次数限制中间件：限制单智能体的模型调用次数

6. TodoListMiddleware
    待办事项中间件：在模型调用前将待办事项列表注
"""

from __future__ import annotations

from typing import Any

from langchain.agents.middleware import (
    AgentMiddleware,
    ModelCallLimitMiddleware,
    SummarizationMiddleware,
    TodoListMiddleware,
    ToolCallRequest,
    ToolRetryMiddleware,
)
from langchain_core.messages import ToolMessage
from langgraph.config import get_stream_writer
from langgraph.types import Command

from app.services.agent.prompts import get_summarization_middleware_prompt
from app.services.tools.tool_log import append_tool_call
from app.services.utils import _get_env_int, normalize_tool_args

# Agent middleware configuration
MODEL_CALL_RUN_LIMIT = _get_env_int("WORDAGENT_AGENT_RECURSION_LIMIT", 100)
MODEL_CALL_LIMIT_EXIT_BEHAVIOR = "end"
SUMMARIZATION_TRIGGER_TOKENS = _get_env_int(
    "WORDAGENT_SUMMARIZATION_TRIGGER_TOKENS",
    80_000,
)
SUMMARIZATION_KEEP_TOKENS = _get_env_int(
    "WORDAGENT_SUMMARIZATION_KEEP_TOKENS",
    20_000,
)
TOOL_MAX_RETRIES = 2
TOOL_RETRY_ON_FAILURE = "continue"
TOOL_RETRY_BACKOFF_FACTOR = 2.0
TOOL_RETRY_INITIAL_DELAY = 1.0
TOOL_RETRY_MAX_DELAY = 10.0
TOOL_RETRY_JITTER = True

_BUILTIN_TOOL_NAMES = {
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


def get_summarization_limits() -> tuple[int, int]:
    """读取单智能体摘要阈值，并保证保留量小于触发量。"""
    trigger_tokens = SUMMARIZATION_TRIGGER_TOKENS
    keep_tokens = SUMMARIZATION_KEEP_TOKENS
    if keep_tokens >= trigger_tokens:
        keep_tokens = max(1, trigger_tokens // 4)
    return trigger_tokens, keep_tokens


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


# region MIDDLEWARE CLASSES


class NotifyingSummarizationMiddleware(SummarizationMiddleware):
    """在官方摘要执行前后发送前端可消费的 custom stream 事件。"""

    @staticmethod
    def _write_event(status: str, content: str) -> None:
        try:
            writer = get_stream_writer()
        except RuntimeError:
            return
        if writer:
            writer({"type": "context_compaction", "status": status, "content": content})

    def _create_summary(self, messages_to_summarize):
        self._write_event("started", "正在整理较早的对话上下文")
        try:
            return super()._create_summary(messages_to_summarize)
        finally:
            self._write_event("completed", "对话上下文整理完成")

    async def _acreate_summary(self, messages_to_summarize):
        self._write_event("started", "正在整理较早的对话上下文")
        try:
            return await super()._acreate_summary(messages_to_summarize)
        finally:
            self._write_event("completed", "对话上下文整理完成")


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


def build_agent_middleware(*, summary_model) -> list:
    """按当前模型构造单智能体中间件链。"""
    trigger_tokens, keep_tokens = get_summarization_limits()
    return [
        TODO_LIST_MIDDLEWARE,
        MODEL_CALL_LIMIT_MIDDLEWARE,
        NotifyingSummarizationMiddleware(
            model=summary_model,
            trigger=("tokens", trigger_tokens),
            keep=("tokens", keep_tokens),
            summary_prompt=get_summarization_middleware_prompt(),
        ),
        TOOL_NORMALIZATION_AND_LOGGING_MIDDLEWARE,
        TOOL_RETRY_MIDDLEWARE,
    ]
