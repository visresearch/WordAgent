from functools import lru_cache
from pathlib import Path


_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"

# 核心提示：始终注入系统提示（身份、风格、规则、工具策略）
_CORE_PROMPT_FILES = [
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
    "system-prompt-tool-usage-generate-document.md",
    "system-prompt-tool-usage-delete-document.md",
    "system-prompt-tool-usage-subagent-guidance.md",
    "system-prompt-tool-usage-web-fetch.md",
]

# 兼容旧调用：与 _CORE_PROMPT_FILES 保持一致。
_COMMON_PROMPT_FILES = _CORE_PROMPT_FILES


@lru_cache(maxsize=64)
def _read_prompt_file(file_name: str) -> str:
    """读取单个 markdown 提示文件。"""
    file_path = _PROMPTS_DIR / file_name
    if not file_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {file_path}")
    return file_path.read_text(encoding="utf-8").strip()


def get_core_prompts(mode: str | None = None) -> list[str]:
    """返回核心提示列表（始终注入系统提示）。"""
    return [_read_prompt_file(f) for f in _CORE_PROMPT_FILES]


def get_agent_prompt_parts(mode: str | None = None) -> list[str]:
    """按顺序返回从 markdown 加载的系统提示片段。"""
    return [_read_prompt_file(f) for f in _COMMON_PROMPT_FILES]


def get_agent_prompt(mode: str | None = None) -> str:
    """兼容旧调用：将全部提示合并为单个系统提示。"""
    return "\n\n".join(get_agent_prompt_parts(mode=mode))