"""主智能体调用子智能体的工具。"""

from typing import Literal

from langchain_core.tools import tool

from app.services.agent.prompts import get_tool_description
from app.services.agent.subAgent import run_sub_agent_task


# ---------------------------------------------------------------------------
# 工具定义
# ---------------------------------------------------------------------------


@tool(description=get_tool_description("run_sub_agent"))
def run_sub_agent(
    description: str,
    prompt: str,
    agent_type: Literal["reviewer", "explorer"],
) -> str:
    """创建并运行子智能体来完成专项任务。"""
    return run_sub_agent_task(
        description=description,
        prompt=prompt,
        agent_type=agent_type,
    )
