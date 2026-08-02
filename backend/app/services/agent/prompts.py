from functools import lru_cache
from pathlib import Path

from app.services.tools.prompts import get_tool_description, read_tool_prompt

# 非工具类片段仍放在 agent/prompts
_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"

# 各模式只加载与其实际工具和职责相关的片段。
_LOCAL_BASE_PROMPT_FILES = [
    "agent-prompt-identity.md",
    "system-prompt-common-rules.md",
]

_READ_ONLY_TOOL_PROMPT_FILES = [
    "system-prompt-tool-usage-read-document.md",
    "system-prompt-tool-usage-search-document.md",
    "system-prompt-tool-usage-load-skill-context.md",
]

_FILE_TOOL_PROMPT_FILES = [
    "system-prompt-tool-usage-list-file.md",
    "system-prompt-tool-usage-read-file.md",
    "system-prompt-tool-usage-edit-file.md",
]

_AGENT_DOCUMENT_FOUNDATION_FILES = [
    "system-prompt-default-document-style.md",
    "system-prompt-tool-usage-strategy.md",
]

_AGENT_MUTATION_TOOL_PROMPT_FILES = [
    "system-prompt-tool-usage-create-document.md",
    "system-prompt-tool-usage-generate-document.md",
    "system-prompt-tool-usage-delete-document.md",
    "system-prompt-tool-usage-edit-document.md",
    "system-prompt-tool-usage-insert-break.md",
    # 单智能体模式暂时停用子智能体提示词；保留文件，后续恢复功能时再启用。
    # "system-prompt-tool-usage-subagent-guidance.md",
    "system-prompt-tool-usage-python-repl.md",
]

_AGENT_REVIEW_PROMPT_FILES = [
    "system-prompt-document-reviewer.md",
]

_SHARED_PROMPT_NAMES = frozenset(
    _READ_ONLY_TOOL_PROMPT_FILES
    + _FILE_TOOL_PROMPT_FILES
    + _AGENT_DOCUMENT_FOUNDATION_FILES
    + _AGENT_MUTATION_TOOL_PROMPT_FILES
)

_MODE_PROMPT_FILES = {
    "agent": (
        _LOCAL_BASE_PROMPT_FILES
        + _AGENT_DOCUMENT_FOUNDATION_FILES
        + _READ_ONLY_TOOL_PROMPT_FILES
        + ["system-prompt-project-directory-guide.md"]
        + _FILE_TOOL_PROMPT_FILES
        + _AGENT_MUTATION_TOOL_PROMPT_FILES
        + _AGENT_REVIEW_PROMPT_FILES
    ),
    "ask": (
        _LOCAL_BASE_PROMPT_FILES
        + _READ_ONLY_TOOL_PROMPT_FILES
        + ["system-prompt-project-directory-guide.md"]
        + _FILE_TOOL_PROMPT_FILES
    ),
}


def _normalize_mode(mode: str | None) -> str:
    """标准化对话模式：plan 暂时按 agent 处理。"""
    normalized = (mode or "agent").strip().lower()
    if normalized == "plan":
        return "agent"
    if normalized not in _MODE_PROMPT_FILES:
        return "agent"
    return normalized


@lru_cache(maxsize=64)
def _read_local_prompt_file(file_name: str) -> str:
    """读取 agent/prompts 下的非工具片段。"""
    file_path = _PROMPTS_DIR / file_name
    if not file_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {file_path}")
    return file_path.read_text(encoding="utf-8").strip()


def _load_core_prompt_fragment(file_name: str) -> str:
    if file_name in _SHARED_PROMPT_NAMES:
        return read_tool_prompt(file_name)
    return _read_local_prompt_file(file_name)


def get_core_prompts(mode: str | None = None) -> list[str]:
    """返回核心提示列表（按模式筛选）。"""
    normalized_mode = _normalize_mode(mode)
    prompt_files = _MODE_PROMPT_FILES[normalized_mode]
    return [_load_core_prompt_fragment(f) for f in prompt_files]


def get_agent_prompt_parts(mode: str | None = None) -> list[str]:
    """按顺序返回从 markdown 加载的系统提示片段（按模式筛选）。"""
    return get_core_prompts(mode=mode)


def get_agent_prompt(mode: str | None = None) -> str:
    """兼容旧调用：将全部提示合并为单个系统提示。"""
    return "\n\n".join(get_agent_prompt_parts(mode=mode))


@lru_cache(maxsize=1)
def get_compaction_summary_prompt() -> str:
    """加载重量压缩的结构化摘要提示词。"""
    return _read_local_prompt_file("system-prompt-context-compaction-summary.md")


__all__ = [
    "get_tool_description",
    "get_core_prompts",
    "get_agent_prompt_parts",
    "get_agent_prompt",
    "get_compaction_summary_prompt",
]
