from functools import lru_cache
from pathlib import Path


_SKILLS_DIR = Path(__file__).resolve().parent / "skills"

# 核心技能：始终加载到系统提示中（身份、风格、基本规则）
_CORE_SKILL_FILES = [
    "identity.md",
    "style.md",
    "no_tool_scenario.md",
    "tool_strategy.md",
    "read_document.md",
    "search_documnet.md",
    "execution_rules.md",
    "subAgent.md",
]

# 所有技能文件
_COMMON_SKILL_FILES = [
    "identity.md",
    "style.md",
    "tool_strategy.md",
    "search_documnet.md",
    "read_document.md",
    "no_tool_scenario.md",
    "execution_rules.md",
    "generate_document.md",
    "delete_document.md",
    "web_tools.md",
]


@lru_cache(maxsize=64)
def _read_skill_file(file_name: str) -> str:
    """读取单个 markdown skill 文件。"""
    file_path = _SKILLS_DIR / file_name
    if not file_path.exists():
        raise FileNotFoundError(f"skill 文件不存在: {file_path}")
    return file_path.read_text(encoding="utf-8").strip()


def get_core_skills(mode: str | None = None) -> list[str]:
    """返回核心技能列表（始终注入的系统提示）。"""
    return [_read_skill_file(f) for f in _CORE_SKILL_FILES]


def get_agent_prompt_skills(mode: str | None = None) -> list[str]:
    """返回按顺序注入的系统提示技能列表（从 markdown 文件加载）。"""
    return [_read_skill_file(f) for f in _COMMON_SKILL_FILES]


def get_agent_prompt(mode: str | None = None) -> str:
    """兼容旧调用: 合并全部技能为单个系统提示。"""
    return "\n\n".join(get_agent_prompt_skills(mode=mode))
