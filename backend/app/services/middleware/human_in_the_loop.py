"""Pause ask_user tool calls for the user's response."""

from langchain.agents.middleware import HumanInTheLoopMiddleware


def build_human_in_the_loop_middleware() -> HumanInTheLoopMiddleware:
    return HumanInTheLoopMiddleware(interrupt_on={"ask_user": {"allowed_decisions": ["respond"]}})
