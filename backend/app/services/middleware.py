"""
langchain 中间件
1. NotifyingSummarizationMiddleware
    上下文摘要中间件：在模型调用前对历史消息进行摘要，减少 token 消耗。

2. ToolNormalizationAndLoggingMiddleware
    工具调用参数归一化和结果持久化中间件：在每次工具调用前对参数进行归一化，并在工具调用后将最终结果持久化到数据库。

3. ToolRetryMiddleware
    工具调用重试中间件：在工具调用失败时进行重试

4. InvalidToolCallMiddleware
    模型非法工具调用校正中间件：当模型返回 invalid_tool_calls 时，要求模型重新生成合法 JSON。

5. ModelCallLimitMiddleware
    模型调用次数限制中间件：限制单智能体的模型调用次数

6. TodoListMiddleware
    待办事项中间件：为智能体提供待办事项状态管理。
"""

from __future__ import annotations

from typing import Any

from langchain.agents.middleware import (
    AgentMiddleware,
    ModelCallLimitMiddleware,
    ModelRequest,
    ModelResponse,
    SummarizationMiddleware,
    TodoListMiddleware,
    ToolCallRequest,
    ToolRetryMiddleware,
)
from langchain_core.messages import AIMessage, RemoveMessage, SystemMessage, ToolMessage
from langchain_core.messages.utils import count_tokens_approximately
from langgraph.config import get_stream_writer
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langgraph.types import Command

from app.core.logging import get_logger
from app.services.agent.prompts import get_summarization_middleware_prompt
from app.services.tools.tool_log import append_tool_call
from app.services.utils import _get_env_float, _get_env_int, normalize_tool_args

logger = get_logger(__name__)


MAX_CONTEXT_TOKENS = _get_env_int("WORDAGENT_MAX_CONTEXT_TOKENS", 258000)

MODEL_CALL_RUN_LIMIT = _get_env_int("WORDAGENT_AGENT_RECURSION_LIMIT", 100)
MODEL_CALL_LIMIT_EXIT_BEHAVIOR = "end"
INVALID_TOOL_CALL_MAX_RETRIES = _get_env_int("WORDAGENT_INVALID_TOOL_CALL_MAX_RETRIES", 1)

SUMMARIZATION_TRIGGER_PCT = _get_env_float("WORDAGENT_HEAVY_COMPACT_TRIGGER_PCT", 93.0)
SUMMARIZATION_KEEP_PCT = _get_env_float("WORDAGENT_HEAVY_COMPACT_KEEP_PCT", 8.0)

TOOL_MAX_RETRIES = _get_env_int("WORDAGENT_TOOL_MAX_RETRIES", 2)
TOOL_RETRY_ON_FAILURE = "continue"
TOOL_RETRY_BACKOFF_FACTOR = _get_env_float("WORDAGENT_TOOL_RETRY_BACKOFF_FACTOR", 2.0)
TOOL_RETRY_INITIAL_DELAY = _get_env_float("WORDAGENT_TOOL_RETRY_INITIAL_DELAY", 1.0)
TOOL_RETRY_MAX_DELAY = _get_env_float("WORDAGENT_TOOL_RETRY_MAX_DELAY", 10.0)
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
    """按总上下文窗口的百分比计算摘要触发量和保留量。"""
    trigger_pct = min(SUMMARIZATION_TRIGGER_PCT, 100.0)
    keep_pct = min(SUMMARIZATION_KEEP_PCT, 100.0)
    trigger_tokens = max(1, int(MAX_CONTEXT_TOKENS * trigger_pct / 100))
    keep_tokens = max(1, int(MAX_CONTEXT_TOKENS * keep_pct / 100))
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


class InvalidToolCallError(RuntimeError):
    """模型多次生成无法解析的工具调用参数。"""

# region Middleware Classes

class InvalidToolCallMiddleware(AgentMiddleware):
    """校正模型生成的 ``invalid_tool_calls``，避免直接结束 agent loop。

    ``ToolRetryMiddleware`` 只包裹已经进入 ToolNode 的工具执行函数；模型输出
    在解析阶段失败时不会进入 ToolNode，因此需要在模型调用边界单独重试。校正
    指令只通过临时的 ``ModelRequest`` 传给模型，不会写入会话 checkpoint。
    """

    def __init__(self, *, max_retries: int = INVALID_TOOL_CALL_MAX_RETRIES) -> None:
        super().__init__()
        if max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        self.max_retries = max_retries
        self.tools = []

    @staticmethod
    def _find_invalid_tool_calls(response: ModelResponse | AIMessage) -> list[dict[str, Any]]:
        messages = response.result if isinstance(response, ModelResponse) else [response]
        invalid_calls: list[dict[str, Any]] = []
        for message in messages:
            if not isinstance(message, AIMessage):
                continue
            # 如果同一响应同时含有合法调用，优先执行合法调用，避免重试造成重复写入。
            if getattr(message, "tool_calls", None):
                continue
            for call in getattr(message, "invalid_tool_calls", None) or []:
                if isinstance(call, dict):
                    invalid_calls.append(call)
        return invalid_calls

    @staticmethod
    def _repair_request(request: ModelRequest, invalid_calls: list[dict[str, Any]]) -> ModelRequest:
        names = sorted({str(call.get("name") or "unknown") for call in invalid_calls})
        name_text = ", ".join(names)
        repair_text = (
            "\n\n[Tool call correction]\n"
            f"The previous response contained an invalid tool call for: {name_text}. "
            "Its arguments were not valid JSON and the tool was not executed. "
            "Regenerate the tool call now using the exact tool schema. "
            "Return valid JSON arguments only (no Markdown fences, comments, or trailing commas). "
            "If the payload is large, split it into smaller sequential tool calls."
        )
        base_message = request.system_message
        if base_message is None:
            system_content: Any = repair_text.lstrip()
        elif isinstance(base_message.content, list):
            system_content = [*base_message.content, {"type": "text", "text": repair_text}]
        else:
            system_content = f"{base_message.content}{repair_text}"
        return request.override(system_message=SystemMessage(content=system_content))

    @staticmethod
    def _notify_retry(tool_names: str, attempt: int) -> None:
        try:
            writer = get_stream_writer()
        except RuntimeError:
            return
        if writer:
            writer(
                {
                    "type": "status",
                    "content": f"⚠️ {tool_names} 工具参数格式无效，正在重新生成（第 {attempt} 次）",
                }
            )

    def wrap_model_call(self, request: ModelRequest, handler):
        current_request = request
        for attempt in range(self.max_retries + 1):
            response = handler(current_request)
            invalid_calls = self._find_invalid_tool_calls(response)
            if not invalid_calls:
                return response

            names = ", ".join(sorted({str(call.get("name") or "unknown") for call in invalid_calls}))
            logger.warning(
                "[InvalidToolCall] 模型生成非法工具调用: tools=%s attempt=%d args_lengths=%s",
                names,
                attempt + 1,
                [len(str(call.get("args") or "")) for call in invalid_calls],
            )
            if attempt >= self.max_retries:
                raise InvalidToolCallError(f"模型连续生成无效工具调用参数: {names}")

            self._notify_retry(names, attempt + 1)
            current_request = self._repair_request(current_request, invalid_calls)
        raise InvalidToolCallError("模型工具调用校正失败")

    async def awrap_model_call(self, request: ModelRequest, handler):
        current_request = request
        for attempt in range(self.max_retries + 1):
            response = await handler(current_request)
            invalid_calls = self._find_invalid_tool_calls(response)
            if not invalid_calls:
                return response

            names = ", ".join(sorted({str(call.get("name") or "unknown") for call in invalid_calls}))
            logger.warning(
                "[InvalidToolCall] 模型生成非法工具调用: tools=%s attempt=%d args_lengths=%s",
                names,
                attempt + 1,
                [len(str(call.get("args") or "")) for call in invalid_calls],
            )
            if attempt >= self.max_retries:
                raise InvalidToolCallError(f"模型连续生成无效工具调用参数: {names}")

            self._notify_retry(names, attempt + 1)
            current_request = self._repair_request(current_request, invalid_calls)
        raise InvalidToolCallError("模型工具调用校正失败")



class NotifyingSummarizationMiddleware(SummarizationMiddleware):
    """使用完整上下文估算触发官方摘要，并同步通知前端 token 变化。"""

    def __init__(
        self,
        *args,
        system_prompt: str = "",
        tools: list | None = None,
        max_context_tokens: int = MAX_CONTEXT_TOKENS,
        **kwargs,
    ) -> None:
        # 显式传入无 usage scaling 的历史计数器，避免历史 AIMessage 的总用量
        # 被误当作当前消息体大小；完整上下文估算在下方单独处理。
        kwargs["token_counter"] = lambda messages: count_tokens_approximately(
            messages,
            use_usage_metadata_scaling=False,
        )
        super().__init__(*args, **kwargs)
        self._system_message = SystemMessage(content=system_prompt) if system_prompt else None
        self._tools = list(tools or [])
        self._max_context_tokens = max(1, int(max_context_tokens))

    @staticmethod
    def _write_event(
        status: str,
        content: str,
        *,
        current_tokens: int | None = None,
        max_tokens: int | None = None,
    ) -> None:
        try:
            writer = get_stream_writer()
        except RuntimeError:
            return
        if writer:
            event: dict[str, Any] = {
                "type": "context_compaction",
                "status": status,
                "content": content,
            }
            if current_tokens is not None:
                event["current_tokens"] = max(0, int(current_tokens))
            if max_tokens is not None:
                event["max_tokens"] = max(1, int(max_tokens))
            writer(event)

    @staticmethod
    def _raw_history_tokens(messages: list) -> int:
        return count_tokens_approximately(messages, use_usage_metadata_scaling=False)

    def _baseline_overhead_tokens(self) -> int:
        system_messages = [self._system_message] if self._system_message is not None else []
        return count_tokens_approximately(
            system_messages,
            tools=self._tools,
            use_usage_metadata_scaling=False,
        )

    def _fixed_overhead_tokens(self, messages: list) -> int:
        """用最近一次真实 input_tokens 校准系统提示词和工具的固定开销。"""
        baseline = self._baseline_overhead_tokens()
        latest_summary_index = max(
            (
                index
                for index, message in enumerate(messages)
                if getattr(message, "additional_kwargs", {}).get("lc_source") == "summarization"
            ),
            default=-1,
        )
        for index in range(len(messages) - 1, latest_summary_index, -1):
            message = messages[index]
            if not isinstance(message, AIMessage):
                continue
            usage = getattr(message, "usage_metadata", None)
            if not isinstance(usage, dict):
                continue
            try:
                input_tokens = int(usage.get("input_tokens", 0))
            except (TypeError, ValueError):
                continue
            if input_tokens > 0:
                history_before_response = self._raw_history_tokens(messages[:index])
                return max(baseline, input_tokens - history_before_response)
        return baseline

    def _context_tokens(self, messages: list, *, fixed_overhead: int | None = None) -> int:
        overhead = self._fixed_overhead_tokens(messages) if fixed_overhead is None else fixed_overhead
        return max(0, overhead) + self._raw_history_tokens(messages)

    def _completed_content(self, current_tokens: int) -> str:
        if current_tokens > self._max_context_tokens:
            return "⚠️ 上下文压缩完成，但系统提示词和工具定义占用较大，当前估算仍超过配置上限"
        return "✅ 上下文压缩完成"

    def before_model(self, state, runtime):
        messages = state["messages"]
        self._ensure_message_ids(messages)
        total_tokens = self._context_tokens(messages)
        if not self._should_summarize(messages, total_tokens):
            return None

        cutoff_index = self._determine_cutoff_index(messages)
        if cutoff_index <= 0:
            return None

        fixed_overhead = self._fixed_overhead_tokens(messages)
        messages_to_summarize, preserved_messages = self._partition_messages(messages, cutoff_index)
        self._write_event(
            "started",
            "🗜️ 正在自动压缩上下文",
            current_tokens=total_tokens,
            max_tokens=self._max_context_tokens,
        )
        try:
            summary = self._create_summary(messages_to_summarize)
        except Exception:
            self._write_event("failed", "❌ 上下文压缩失败")
            raise

        replacement_messages = [*self._build_new_messages(summary), *preserved_messages]
        current_tokens = self._context_tokens(replacement_messages, fixed_overhead=fixed_overhead)
        self._write_event(
            "completed",
            self._completed_content(current_tokens),
            current_tokens=current_tokens,
            max_tokens=self._max_context_tokens,
        )
        return {"messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES), *replacement_messages]}

    async def abefore_model(self, state, runtime):
        messages = state["messages"]
        self._ensure_message_ids(messages)
        total_tokens = self._context_tokens(messages)
        if not self._should_summarize(messages, total_tokens):
            return None

        cutoff_index = self._determine_cutoff_index(messages)
        if cutoff_index <= 0:
            return None

        fixed_overhead = self._fixed_overhead_tokens(messages)
        messages_to_summarize, preserved_messages = self._partition_messages(messages, cutoff_index)
        self._write_event(
            "started",
            "🗜️ 正在自动压缩上下文",
            current_tokens=total_tokens,
            max_tokens=self._max_context_tokens,
        )
        try:
            summary = await self._acreate_summary(messages_to_summarize)
        except Exception:
            self._write_event("failed", "❌ 上下文压缩失败")
            raise

        replacement_messages = [*self._build_new_messages(summary), *preserved_messages]
        current_tokens = self._context_tokens(replacement_messages, fixed_overhead=fixed_overhead)
        self._write_event(
            "completed",
            self._completed_content(current_tokens),
            current_tokens=current_tokens,
            max_tokens=self._max_context_tokens,
        )
        return {"messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES), *replacement_messages]}


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

INVALID_TOOL_CALL_MIDDLEWARE = InvalidToolCallMiddleware()

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


def build_agent_middleware(*, summary_model, system_prompt: str = "", tools: list | None = None) -> list:
    """按当前模型构造单智能体中间件链。"""
    trigger_tokens, keep_tokens = get_summarization_limits()
    return [
        TODO_LIST_MIDDLEWARE,
        MODEL_CALL_LIMIT_MIDDLEWARE,
        INVALID_TOOL_CALL_MIDDLEWARE,
        NotifyingSummarizationMiddleware(
            model=summary_model,
            trigger=("tokens", trigger_tokens),
            keep=("tokens", keep_tokens),
            summary_prompt=get_summarization_middleware_prompt(),
            system_prompt=system_prompt,
            tools=tools,
            max_context_tokens=MAX_CONTEXT_TOKENS,
        ),
        TOOL_NORMALIZATION_AND_LOGGING_MIDDLEWARE,
        TOOL_RETRY_MIDDLEWARE,
    ]
