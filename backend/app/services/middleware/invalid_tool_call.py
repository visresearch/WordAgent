"""Repair invalid tool calls at the model boundary."""

from __future__ import annotations

from typing import Any

from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
from langchain_core.messages import AIMessage, SystemMessage
from langgraph.config import get_stream_writer

from app.core.logging import get_logger
from app.services.utils import _get_env_int

logger = get_logger(__name__)

INVALID_TOOL_CALL_MAX_RETRIES = _get_env_int("WORDAGENT_INVALID_TOOL_CALL_MAX_RETRIES", 2)


class InvalidToolCallError(RuntimeError):
    """模型多次生成无法解析的工具调用参数。"""


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


INVALID_TOOL_CALL_MIDDLEWARE = InvalidToolCallMiddleware()
