"""Limit model calls within one agent run."""

from langchain.agents.middleware import ModelCallLimitMiddleware

from app.services.utils import _get_env_int

MODEL_CALL_RUN_LIMIT = _get_env_int("WORDAGENT_AGENT_RECURSION_LIMIT", 50)
MODEL_CALL_LIMIT_EXIT_BEHAVIOR = "end"

MODEL_CALL_LIMIT_MIDDLEWARE = ModelCallLimitMiddleware(
    run_limit=MODEL_CALL_RUN_LIMIT,
    exit_behavior=MODEL_CALL_LIMIT_EXIT_BEHAVIOR,
)
