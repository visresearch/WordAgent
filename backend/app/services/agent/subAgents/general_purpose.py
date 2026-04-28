"""
通用子智能体 (General Purpose Agent)

用于执行多步骤复杂任务。
"""

from pathlib import Path
from typing import Any


class GeneralPurposeSubAgent:
    """通用子智能体。用于执行多步骤复杂任务。"""

    agent_type: str = "general-purpose"
    config: dict[str, Any] = {
        "name": "GeneralPurpose",
        "description": "通用目的智能体，执行多步骤复杂任务",
        "model": None,
        "max_turns": 25,
        "background": False,
    }

    ALLOWED_TOOLS: list[str] = [
        "read_document",
        "search_documnet",
        "generate_document",
        "delete_document",
    ]

    def get_system_prompt(self, context: dict[str, Any] | None = None) -> str:
        """从 md 文件读取提示词。"""
        prompt_file = Path(__file__).parent.parent / "prompts" / "agent-prompt-general-purpose.md"
        if prompt_file.exists():
            return prompt_file.read_text(encoding="utf-8").strip()
        return "You are a general-purpose document assistant. Use available tools to complete tasks."

    def get_allowed_tools(self) -> list[str]:
        return self.ALLOWED_TOOLS


general_purpose_agent = GeneralPurposeSubAgent()
