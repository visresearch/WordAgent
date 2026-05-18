"""Python execution tools (agent-only)."""

from __future__ import annotations

from langchain_experimental.tools import PythonREPLTool


def build_python_repl(description: str):
    """Construct a Python REPL tool with project-specific description."""

    python_repl = PythonREPLTool()
    if description:
        python_repl.description = description
    return python_repl


__all__ = ["build_python_repl"]
