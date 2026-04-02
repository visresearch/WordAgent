"""LangGraph dev entrypoint for WordAgent project (single-agent only)."""

import os

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver

from app.services.agent.tools.tools import ALL_TOOLS
from app.services.llm_client import get_llm_init_kwargs, resolve_model


def _build_project_graph():
    """Build the project graph for LangGraph dev server."""
    # Optional override in shell: set LANGGRAPH_DEV_MODEL=qwen-max
    selected_model = os.getenv("LANGGRAPH_DEV_MODEL", "auto")
    model_name = resolve_model(selected_model)
    llm_kwargs = get_llm_init_kwargs(model_name)
    llm = init_chat_model(**llm_kwargs)
    return create_agent(
        model=llm,
        tools=ALL_TOOLS,
        checkpointer=InMemorySaver(),
    )


graph = _build_project_graph()
