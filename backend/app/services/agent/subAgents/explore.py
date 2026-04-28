"""
探索子智能体 (Explore Agent)

专门用于快速搜索和探索文档内容。
"""

from pathlib import Path
from typing import Any


class ExploreSubAgent:
    """探索子智能体。专门用于快速定位文档内容和分析结构。"""

    agent_type: str = "explore"
    config: dict[str, Any] = {
        "name": "Explore",
        "description": "文档搜索和探索专家，快速定位内容并分析文档结构",
        "model": None,
        "max_turns": 10,
        "background": False,
    }

    ALLOWED_TOOLS: list[str] = [
        "read_document",
        "search_documnet",
    ]

    def get_system_prompt(self, context: dict[str, Any] | None = None) -> str:
        """从 md 文件读取提示词。"""
        prompt_file = Path(__file__).parent.parent / "prompts" / "agent-prompt-explore.md"
        if prompt_file.exists():
            return prompt_file.read_text(encoding="utf-8").strip()
        return "You are a document search specialist. Use search_documnet and read_document to explore content."

    def get_allowed_tools(self) -> list[str]:
        return self.ALLOWED_TOOLS


explore_agent = ExploreSubAgent()
