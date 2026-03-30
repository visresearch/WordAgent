"""单智能体技能加载工具。"""

from langchain_core.tools import tool


@tool
def load_skill(skill_name: str) -> str:
    """加载指定的专业技能提示，获取详细的工具使用规则和操作指南。"""
    from app.services.agent.prompts import _ON_DEMAND_SKILLS, get_on_demand_skill

    content = get_on_demand_skill(skill_name)
    if content is None:
        available = ", ".join(_ON_DEMAND_SKILLS.keys())
        return f"错误: 未知技能 '{skill_name}'。可用技能: {available}"
    print(f"[load_skill] ✅ 已加载技能: {skill_name}")
    return content
