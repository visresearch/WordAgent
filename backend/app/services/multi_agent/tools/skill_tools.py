"""Tools for using local markdown skills in the main agent."""

from langchain_core.tools import tool

from app.services.agent.skills import load_skill_context as load_skill_context_impl


@tool
def load_skill_context(skill_name: str) -> str:
    """Load guidance content from a specific discovered skill for current writing task."""
    return load_skill_context_impl(skill_name)


__all__ = ["load_skill_context"]
