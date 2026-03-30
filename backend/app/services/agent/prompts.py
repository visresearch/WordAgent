from functools import lru_cache
from pathlib import Path


_SKILLS_DIR = Path(__file__).resolve().parent / "skills"

# 核心技能：始终加载到系统提示中（身份、风格、基本规则）
_CORE_SKILL_FILES = [
    "identity.md",
    "style.md",
    "no_tool_scenario.md",
]

# 按需技能：通过 load_skill 工具按需加载（渐进式披露）
_ON_DEMAND_SKILLS: dict[str, str] = {
    "tool_strategy": "工具选择策略 — 当用户需要进行文档操作时加载，了解 query/read/edit 的使用优先级和组合方式",
    "search_documnet": "search_documnet 工具详细规则 — 在需要查找/定位文档中特定内容时加载",
    "read_document": "read_document 工具详细规则 — 在需要读取文档段落内容时加载",
    "edit_document": "edit_document 工具详细规则 — 在需要删除/插入/替换文档内容时加载（包含 JSON 格式规范和最小改动原则）",
    "execution_rules": "执行规则 — 在开始执行任何文档操作前加载，包含调用前说明意图、最小改动等关键约束",
    "web_tools": "web_search / web_fetch 工具规则 — 在需要搜索或获取网页信息时加载",
}

# 所有技能文件
_COMMON_SKILL_FILES = [
    "identity.md",
    "style.md",
    "tool_strategy.md",
    "search_documnet.md",
    "read_document.md",
    "no_tool_scenario.md",
    "execution_rules.md",
    "edit_document.md",
    "web_tools.md",
]


@lru_cache(maxsize=64)
def _read_skill_file(file_name: str) -> str:
    """读取单个 markdown skill 文件。"""
    file_path = _SKILLS_DIR / file_name
    if not file_path.exists():
        raise FileNotFoundError(f"skill 文件不存在: {file_path}")
    return file_path.read_text(encoding="utf-8").strip()


def get_on_demand_skill(skill_name: str) -> str | None:
    """按名称加载按需技能，返回内容或 None。"""
    if skill_name not in _ON_DEMAND_SKILLS:
        return None
    file_name = f"{skill_name}.md"
    return _read_skill_file(file_name)


def get_on_demand_skill_index() -> str:
    """生成按需技能索引提示，告知 Agent 可用技能及加载时机。"""
    lines = [
        "你拥有以下可按需加载的技能。在执行相关任务前，先调用 load_skill 工具加载对应技能获取详细指令：",
    ]
    for name, desc in _ON_DEMAND_SKILLS.items():
        lines.append(f"- {name}: {desc}")
    lines.append("")
    lines.append("⚠️ 技能加载规则：")
    lines.append("1. 收到文档操作请求时，先加载 tool_strategy 和 execution_rules 了解整体策略")
    lines.append("2. 使用具体工具前，加载对应工具的技能（如使用 edit_document 前加载 edit_document 技能）")
    lines.append("3. 已加载的技能在本次对话中持续有效，无需重复加载")
    lines.append("4. 纯聊天/问答场景无需加载任何技能")
    lines.append("")
    lines.append("⚠️ edit_document 调用前硬性自检（必须全部满足）：")
    lines.append("1. delete-only 场景不要传 document；用 startParaIndex/endParaIndex 或 deleteRanges 即可")
    lines.append("2. insert/replace 场景传 document 时，document.styles 必填，且覆盖所有样式引用")
    lines.append("3. insert/replace 场景中，document.paragraphs 每个段落都必须有 paraIndex（0-based）")
    lines.append("4. 若缺少 styles 或 paraIndex，先补齐参数再调用 edit_document，禁止带缺失字段调用")
    return "\n".join(lines)


def get_core_skills(mode: str | None = None) -> list[str]:
    """返回核心技能列表（始终注入的系统提示）。"""
    return [_read_skill_file(f) for f in _CORE_SKILL_FILES]


def get_agent_prompt_skills(mode: str | None = None) -> list[str]:
    """返回按顺序注入的系统提示技能列表（从 markdown 文件加载）。"""
    return [_read_skill_file(f) for f in _COMMON_SKILL_FILES]


def get_agent_prompt(mode: str | None = None) -> str:
    """兼容旧调用: 合并全部技能为单个系统提示。"""
    return "\n\n".join(get_agent_prompt_skills(mode=mode))
