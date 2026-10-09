"""Assemble middleware shared by the main agent and sub-agents."""

from app.services.agent.prompts import get_summarization_middleware_prompt
from app.services.middleware import (
    INVALID_TOOL_CALL_MIDDLEWARE,
    MAX_CONTEXT_TOKENS,
    MODEL_CALL_LIMIT_MIDDLEWARE,
    TODO_LIST_MIDDLEWARE,
    TOOL_NORMALIZATION_AND_LOGGING_MIDDLEWARE,
    TOOL_RETRY_MIDDLEWARE,
    NotifyingSummarizationMiddleware,
    build_human_in_the_loop_middleware,
    get_summarization_limits,
)


def build_agent_middleware(*, summary_model, system_prompt: str = "", tools: list | None = None) -> list:
    """按当前模型构造单智能体中间件链。"""
    trigger_tokens, keep_tokens = get_summarization_limits()
    return [
        TODO_LIST_MIDDLEWARE,
        MODEL_CALL_LIMIT_MIDDLEWARE,
        INVALID_TOOL_CALL_MIDDLEWARE,
        build_human_in_the_loop_middleware(),
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
