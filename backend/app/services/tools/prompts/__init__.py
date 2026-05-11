"""Shared markdown for tool descriptions and tool-usage system snippets.

Single-agent (`app.services.agent`) and multi-agent (`app.services.multi_agent`)
load from here so tool guidance stays in one place.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_PROMPTS_DIR = Path(__file__).resolve().parent


@lru_cache(maxsize=128)
def read_tool_prompt(file_name: str) -> str:
    """Load a markdown file from this package directory."""
    path = _PROMPTS_DIR / file_name
    if not path.exists():
        raise FileNotFoundError(f"Tool prompt file not found: {path}")
    return path.read_text(encoding="utf-8").strip()


_TOOL_DESCRIPTION_FILES: dict[str, str] = {
    "read_document": "tool-description-read-document.md",
    "generate_document": "tool-description-generate-document.md",
    "delete_document": "tool-description-delete-document.md",
    "search_document": "tool-description-search-document.md",
    "load_skill_context": "tool-description-load-skill-context.md",
    "list_file": "tool-description-list-file.md",
    "read_file": "tool-description-read-file.md",
    "edit_file": "tool-description-edit-file.md",
    "run_sub_agent": "tool-description-run-subagent.md",
    "create_workflow": "tool-description-create-workflow.md",
    "review_document": "tool-description-review-document.md",
}


def get_tool_description(tool_name: str) -> str:
    """Return tool schema description markdown for ``tool_name``."""
    file_name = _TOOL_DESCRIPTION_FILES.get(tool_name)
    if not file_name:
        raise KeyError(f"No description file mapped for tool: {tool_name}")
    return read_tool_prompt(file_name)


__all__ = ["read_tool_prompt", "get_tool_description", "_TOOL_DESCRIPTION_FILES"]
