from functools import lru_cache
from pathlib import Path


_SKILLS_DIR = Path(__file__).resolve().parent / "skills"

_COMMON_SKILL_FILES = [
    "identity.md",
    "style.md",
    "tool_strategy.md",
    "query_document.md",
    "read_document.md",
    "no_tool_scenario.md",
    "execution_rules.md",
]

_ASK_MODE_SKILL_FILES = ["ask_mode_limit.md"]
_AGENT_MODE_SKILL_FILES = ["generate_document.md", "web_tools.md"]


@lru_cache(maxsize=64)
def _read_skill_file(file_name: str) -> str:
    """读取单个 markdown skill 文件。"""
    file_path = _SKILLS_DIR / file_name
    if not file_path.exists():
        raise FileNotFoundError(f"skill 文件不存在: {file_path}")
    return file_path.read_text(encoding="utf-8").strip()


def get_agent_prompt_skills(mode: str | None = None) -> list[str]:
    """返回按顺序注入的系统提示技能列表（从 markdown 文件加载）。"""
    file_names = list(_COMMON_SKILL_FILES)
    if mode == "ask":
        file_names.extend(_ASK_MODE_SKILL_FILES)
    else:
        file_names.extend(_AGENT_MODE_SKILL_FILES)

    return [_read_skill_file(file_name) for file_name in file_names]


def get_agent_prompt(mode: str | None = None) -> str:
    """兼容旧调用: 合并全部技能为单个系统提示。"""
    return "\n\n".join(get_agent_prompt_skills(mode=mode))


# SubAgent 专用技能文件（独立上下文，不继承 MainAgent 的提示）
_SUBAGENT_SKILL_FILES = [
    "style.md",
    "generate_document.md",
]


def get_subagent_prompt() -> str:
    """返回 SubAgent 专用系统提示（独立上下文窗口，只关注文档生成）。"""
    identity = (
        "你是专业的文档生成助手。你的唯一职责是根据提供的任务描述和参考资料，"
        "调用 generate_document 工具生成高质量的 Word 文档。\n\n"
        "# 工作模式\n"
        "- 你会收到一段任务描述，其中包含写作要求和参考资料\n"
        "- 仔细阅读任务描述，理解用户的写作意图\n"
        "- 直接调用 generate_document 工具生成文档，不要在对话中输出长文本\n"
        "- 如果任务描述中提到了文档范围，先调用 read_document 读取原文档\n\n"
        "# 注意事项\n"
        "- 必须调用 generate_document 工具输出文档，不能只用文字回复\n"
        "- 参考资料仅供参考，需要用自己的理解重新组织内容\n"
        "- 确保文档结构完整（标题、正文、段落层级合理）"
    )
    skills = [_read_skill_file(f) for f in _SUBAGENT_SKILL_FILES]
    return identity + "\n\n" + "\n\n".join(skills)
