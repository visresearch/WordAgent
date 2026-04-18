"""Tools for using local markdown skills in the main agent."""

import json

from langchain_core.tools import tool

from app.services.agent.skills import discover_skills, load_skill_context as load_skill_context_impl


@tool
def list_skills() -> str:
    """List all auto-discovered local skills (directories containing SKILL.md)."""
    skills = discover_skills()
    payload = [
        {
            "name": item["name"],
            "folder": item["folder"],
            "description": item["description"],
        }
        for item in skills
    ]
    return json.dumps(payload, ensure_ascii=False)


@tool
def load_skill_context(skill_name: str) -> str:
    """Load guidance content from a specific discovered skill for current writing task."""
    return load_skill_context_impl(skill_name)


__all__ = ["list_skills", "load_skill_context"]
