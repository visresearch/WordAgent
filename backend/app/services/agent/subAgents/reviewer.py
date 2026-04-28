"""
评审子智能体 (Reviewer Agent)

用于专业评审文档内容，提供反馈和建议。
"""

from pathlib import Path
from typing import Any


class ReviewerSubAgent:
    """评审子智能体。用于专业评审文档并提供可操作的反馈。"""

    agent_type: str = "reviewer"
    config: dict[str, Any] = {
        "name": "Reviewer",
        "description": "专业文档评审专家，提供具体的修改建议和可操作的反馈",
        "model": None,
        "max_turns": 15,
        "background": False,
    }

    ALLOWED_TOOLS: list[str] = [
        "read_document",
        "search_documnet",
        "generate_document",
    ]

    def get_system_prompt(self, context: dict[str, Any] | None = None) -> str:
        """从 md 文件读取提示词。"""
        prompt_file = Path(__file__).parent.parent / "prompts" / "agent-prompt-reviewer.md"
        if prompt_file.exists():
            return prompt_file.read_text(encoding="utf-8").strip()
        return "You are a professional document reviewer. Use read_document and search_documnet to review content."

    def get_allowed_tools(self) -> list[str]:
        return self.ALLOWED_TOOLS


reviewer_agent = ReviewerSubAgent()
