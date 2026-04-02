from functools import lru_cache
from pathlib import Path


_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"

# 核心提示：始终加载到系统提示中（身份、风格、基本规则）
_CORE_PROMPT_FILES = [
    "identity.md",
    "style.md",
    "no_tool_scenario.md",
    "execution_rules.md",
    "tool_strategy.md",
    "read_document.md",
    "search_documnet.md",
    "generate_document.md",
    "delete_document.md",
    "subAgent.md",
]

# 兼容旧调用：历史上 get_agent_prompt 使用的提示列表
# 现在与核心技能保持一致，避免双份维护。
_COMMON_PROMPT_FILES = _CORE_PROMPT_FILES


@lru_cache(maxsize=64)
def _read_prompt_file(file_name: str) -> str:
    """读取单个 markdown prompt 文件。"""
    file_path = _PROMPTS_DIR / file_name
    if not file_path.exists():
        raise FileNotFoundError(f"prompt 文件不存在: {file_path}")
    return file_path.read_text(encoding="utf-8").strip()


def get_core_prompts(mode: str | None = None) -> list[str]:
    """返回核心提示列表（始终注入的系统提示）。"""
    return [_read_prompt_file(f) for f in _CORE_PROMPT_FILES]


def get_agent_prompt_parts(mode: str | None = None) -> list[str]:
    """返回按顺序注入的系统提示列表（从 markdown 文件加载）。"""
    return [_read_prompt_file(f) for f in _COMMON_PROMPT_FILES]


def get_agent_prompt(mode: str | None = None) -> str:
    """兼容旧调用: 合并全部提示为单个系统提示。"""
    return "\n\n".join(get_agent_prompt_parts(mode=mode))