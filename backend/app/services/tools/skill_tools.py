"""共享的技能加载工具。"""

from langchain_core.tools import tool

from app.services.agent.skills import load_skill_context as load_skill_context_impl


def build_load_skill_context(description: str | None = None):
    """构造 load_skill_context 工具实例。

    description 为 None 时使用默认 docstring（与历史行为一致）。
    """

    if description is None:

        @tool
        def load_skill_context(skill_name: str) -> str:
            """Load guidance content from a specific discovered skill for current writing task."""
            from langgraph.config import get_stream_writer

            writer = get_stream_writer()
            if writer:
                writer({"type": "status", "content": f"💡 正在读取技能 {skill_name}"})
            return load_skill_context_impl(skill_name)

        return load_skill_context

    @tool(description=description)
    def load_skill_context(skill_name: str) -> str:
        """Load guidance content from a specific discovered skill for current writing task."""
        from langgraph.config import get_stream_writer

        writer = get_stream_writer()
        if writer:
            writer({"type": "status", "content": f"💡 正在读取技能 {skill_name}"})
        return load_skill_context_impl(skill_name)

    return load_skill_context


__all__ = ["build_load_skill_context"]
