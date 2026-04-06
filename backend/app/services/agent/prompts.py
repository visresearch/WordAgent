from functools import lru_cache
from pathlib import Path


_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"

# 公共提示：各模式都注入（身份、风格、规则、通用工具策略）
_COMMON_PROMPT_FILES = [
    "agent-prompt-identity.md",
    "system-prompt-tone-and-style-concise-output.md",
    "system-prompt-doing-tasks-no-unnecessary-additions.md",
    "system-prompt-doing-tasks-read-before-modifying.md",
    "system-prompt-doing-tasks-avoid-over-engineering.md",
    "system-prompt-output-efficiency.md",
    "system-prompt-doing-tasks-security.md",
    "system-prompt-default-recommend-document-style.md",
    "system-prompt-tool-usage-strategy.md",
    "system-prompt-tool-usage-read-document.md",
    "system-prompt-tool-usage-search-document.md",
    "system-prompt-tool-usage-subagent-guidance.md",
    "system-prompt-tool-usage-web-fetch.md",
]

# 仅 agent 模式注入：写作修改相关工具提示
_AGENT_ONLY_PROMPT_FILES = [
    "system-prompt-tool-usage-generate-document.md",
    "system-prompt-tool-usage-delete-document.md",
]

_MODE_PROMPT_FILES = {
    "agent": _COMMON_PROMPT_FILES + _AGENT_ONLY_PROMPT_FILES,
    "ask": _COMMON_PROMPT_FILES,
}

# 兼容旧调用：默认沿用 agent 全量提示。
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
def _read_prompt_file(file_name: str) -> str:
    """读取单个 markdown 提示文件。"""
    file_path = _PROMPTS_DIR / file_name
    if not file_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {file_path}")
    return file_path.read_text(encoding="utf-8").strip()


# ---------------------------------------------------------------------------
# 工具 description 文件映射
# ---------------------------------------------------------------------------
_TOOL_DESCRIPTION_FILES = {
    "read_document": "tool-description-read-document.md",
    "generate_document": "tool-description-generate-document.md",
    "delete_document": "tool-description-delete-document.md",
    "search_document": "tool-description-search-document.md",
    "run_sub_agent": "tool-description-run-subagent.md",
    "web_fetch": "tool-description-web-fetch.md",
}


def get_tool_description(tool_name: str) -> str:
    """根据工具名返回对应的 description markdown 内容。"""
    file_name = _TOOL_DESCRIPTION_FILES.get(tool_name)
    if not file_name:
        raise KeyError(f"No description file mapped for tool: {tool_name}")
    return _read_prompt_file(file_name)


def get_core_prompts(mode: str | None = None) -> list[str]:
    """返回核心提示列表（按模式筛选）。"""
    normalized_mode = _normalize_mode(mode)
    prompt_files = _MODE_PROMPT_FILES.get(normalized_mode, _CORE_PROMPT_FILES)
    return [_read_prompt_file(f) for f in prompt_files]


def get_agent_prompt_parts(mode: str | None = None) -> list[str]:
    """按顺序返回从 markdown 加载的系统提示片段（按模式筛选）。"""
    return get_core_prompts(mode=mode)


def get_agent_prompt(mode: str | None = None) -> str:
    """兼容旧调用：将全部提示合并为单个系统提示。"""
    return "\n\n".join(get_agent_prompt_parts(mode=mode))