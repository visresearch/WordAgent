"""
规划子智能体 (Plan Agent)

用于设计实现方案和规划任务步骤。
"""

from pathlib import Path
from typing import Any


class PlanSubAgent:
    """规划子智能体。用于分析需求并设计实现方案。"""

    agent_type: str = "plan"
    config: dict[str, Any] = {
        "name": "Plan",
        "description": "软件架构师和规划专家，设计实现方案并规划实施步骤",
        "model": None,
        "max_turns": 15,
        "background": False,
    }

    ALLOWED_TOOLS: list[str] = [
        "read_document",
        "search_documnet",
    ]

    def get_system_prompt(self, context: dict[str, Any] | None = None) -> str:
        """从 md 文件读取提示词。"""
        prompt_file = Path(__file__).parent.parent / "prompts" / "agent-prompt-plan.md"
        if prompt_file.exists():
            return prompt_file.read_text(encoding="utf-8").strip()
        return "You are a planning specialist. Use read_document and search_documnet to plan tasks."

    def get_allowed_tools(self) -> list[str]:
        return self.ALLOWED_TOOLS


plan_agent = PlanSubAgent()
