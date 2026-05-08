"""共享的技能加载工具。"""

from langchain_core.tools import tool

from app.services.agent.skills import load_skill_context as load_skill_context_impl


def build_load_skill_context(description: str | None = None):
    """构造 load_skill_context 工具实例。

    必须传入有效 description。未提供时直接报错，避免工具提示词缺失。
    """
    effective_description = (description or "").strip()
    if not effective_description:
        raise ValueError("load_skill_context requires a non-empty description prompt.")

    @tool(description=effective_description)
    def load_skill_context(skill_name: str) -> str:
        """Load guidance content from a specific discovered skill for current writing task."""
        from langgraph.config import get_stream_writer

        writer = get_stream_writer()
        if writer:
            writer({"type": "status", "content": f"💡 正在读取技能： {skill_name}"})
        return load_skill_context_impl(skill_name)

    return load_skill_context


__all__ = ["build_load_skill_context"]
