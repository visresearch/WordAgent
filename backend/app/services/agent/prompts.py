from functools import lru_cache
from pathlib import Path

from app.services.tools.prompts import get_tool_description, read_tool_prompt

# 非工具类片段仍放在 agent/prompts
_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"

# 工具相关片段统一放在 app.services.tools.prompts（与多智能体共用）
_SHARED_TOOL_PROMPT_FILES_BEFORE_PROJECT = [
    "system-prompt-tool-usage-strategy.md",
    "system-prompt-tool-usage-read-document.md",
    "system-prompt-tool-usage-search-document.md",
    "system-prompt-tool-usage-load-skill-context.md",
    "system-prompt-tool-usage-list-file.md",
    "system-prompt-tool-usage-read-file.md",
    "system-prompt-tool-usage-edit-file.md",
]

_SHARED_TOOL_PROMPT_FILES_AFTER_PROJECT = [
    "system-prompt-tool-usage-subagent-guidance.md",
]

_SHARED_TOOL_PROMPT_FILES = _SHARED_TOOL_PROMPT_FILES_BEFORE_PROJECT + _SHARED_TOOL_PROMPT_FILES_AFTER_PROJECT

_AGENT_ONLY_TOOL_PROMPT_FILES = [
    "system-prompt-tool-usage-generate-document.md",
    "system-prompt-tool-usage-delete-document.md",
    "system-prompt-tool-usage-python-repl.md",
]

_SHARED_TOOL_PROMPT_NAMES = frozenset(_SHARED_TOOL_PROMPT_FILES + _AGENT_ONLY_TOOL_PROMPT_FILES)

# 身份、风格、规则 + 非「工具 usage」类文档说明（仍在本目录）
_LOCAL_COMMON_PROMPT_FILES = [
    "agent-prompt-identity.md",
    "system-prompt-tone-and-style-concise-output.md",
    "system-prompt-doing-tasks-no-unnecessary-additions.md",
    "system-prompt-doing-tasks-read-before-modifying.md",
    "system-prompt-doing-tasks-avoid-over-engineering.md",
    "system-prompt-output-efficiency.md",
    "system-prompt-doing-tasks-security.md",
    "system-prompt-default-recommend-document-style.md",
]

_LOCAL_AFTER_FILE_TOOL_USAGE = [
    "system-prompt-project-directory-guide.md",
]

_COMMON_PROMPT_FILES = (
    _LOCAL_COMMON_PROMPT_FILES
    + _SHARED_TOOL_PROMPT_FILES_BEFORE_PROJECT
    + _LOCAL_AFTER_FILE_TOOL_USAGE
    + _SHARED_TOOL_PROMPT_FILES_AFTER_PROJECT
)

_MODE_PROMPT_FILES = {
    "agent": _COMMON_PROMPT_FILES + _AGENT_ONLY_TOOL_PROMPT_FILES,
    "ask": _COMMON_PROMPT_FILES,
}

_CORE_PROMPT_FILES = _MODE_PROMPT_FILES["agent"]


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
    if file_name in _SHARED_TOOL_PROMPT_NAMES:
        return read_tool_prompt(file_name)
    return _read_local_prompt_file(file_name)


def get_core_prompts(mode: str | None = None) -> list[str]:
    """返回核心提示列表（按模式筛选）。"""
    normalized_mode = _normalize_mode(mode)
    prompt_files = _MODE_PROMPT_FILES.get(normalized_mode, _CORE_PROMPT_FILES)
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
