"""LangGraph dev entrypoint for WordAgent project.

Defaults to the real multi-agent graph used by the backend.
You can optionally switch mode via LANGGRAPH_DEV_MODE=single|multi.
"""

import os

from app.services.agent.agent import build_graph
from backend.app.services.agent.tools.tools import ALL_TOOLS
from app.services.multi_agent.agent import _build_multi_agent_graph, _create_llm
from app.services.llm_client import create_llm, resolve_model


def _build_project_graph():
    """Build the project graph for LangGraph dev server."""
    # Optional override in shell: set LANGGRAPH_DEV_MODEL=qwen-max
    selected_model = os.getenv("LANGGRAPH_DEV_MODEL", "auto")
    selected_mode = os.getenv("LANGGRAPH_DEV_MODE", "multi").strip().lower()
    model_name = resolve_model(selected_model)

    if selected_mode == "single":
        llm = create_llm(model_name)
        llm_with_tools = llm.bind_tools(ALL_TOOLS)
        return build_graph(llm_with_tools)

    llm = _create_llm(model_name)
    return _build_multi_agent_graph(llm, model_name)


graph = _build_project_graph()
