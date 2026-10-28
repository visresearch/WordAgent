"""Python execution tools (agent-only)."""

from __future__ import annotations

import threading

from langchain_experimental.tools import PythonREPLTool
from langchain_experimental.utilities import PythonREPL


# PythonREPL redirects process-wide stdout; only REPL calls need this lock.
# The model streams and other tools remain concurrent.
_stdout_lock = threading.Lock()


class _RequestPythonREPLTool(PythonREPLTool):
    def _run(self, query, run_manager=None):
        with _stdout_lock:
            return super()._run(query, run_manager=run_manager)


def build_python_repl(description: str):
    """Construct a Python REPL tool with project-specific description."""

    python_repl = _RequestPythonREPLTool(python_repl=PythonREPL(_globals={}, _locals=None))
    if description:
        python_repl.description = description
    return python_repl


__all__ = ["build_python_repl"]
