"""Compact context and notify clients about token usage."""

from __future__ import annotations

from typing import Any

from langchain.agents.middleware import SummarizationMiddleware
from langchain_core.messages import AIMessage, RemoveMessage, SystemMessage
from langchain_core.messages.utils import count_tokens_approximately
from langgraph.config import get_stream_writer
from langgraph.graph.message import REMOVE_ALL_MESSAGES

from app.services.utils import _get_env_float, _get_env_int

MAX_CONTEXT_TOKENS = _get_env_int("WORDAGENT_MAX_CONTEXT_TOKENS", 258000)
SUMMARIZATION_TRIGGER_PCT = _get_env_float("WORDAGENT_HEAVY_COMPACT_TRIGGER_PCT", 93.0)
SUMMARIZATION_KEEP_PCT = _get_env_float("WORDAGENT_HEAVY_COMPACT_KEEP_PCT", 8.0)


def get_summarization_limits() -> tuple[int, int]:
    """按总上下文窗口的百分比计算摘要触发量和保留量。"""
    trigger_pct = min(SUMMARIZATION_TRIGGER_PCT, 100.0)
    keep_pct = min(SUMMARIZATION_KEEP_PCT, 100.0)
    trigger_tokens = max(1, int(MAX_CONTEXT_TOKENS * trigger_pct / 100))
    keep_tokens = max(1, int(MAX_CONTEXT_TOKENS * keep_pct / 100))
    if keep_tokens >= trigger_tokens:
        keep_tokens = max(1, trigger_tokens // 4)
    return trigger_tokens, keep_tokens


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
