"""
子智能体模块

包含各种类型的子智能体定义和运行逻辑。
"""

from typing import Any

from .explore import ExploreSubAgent, explore_agent
from .general_purpose import GeneralPurposeSubAgent, general_purpose_agent
from .plan import PlanSubAgent, plan_agent
from .reviewer import ReviewerSubAgent, reviewer_agent
from .runner import (
    SUB_AGENT_PROMPT_FILES,
    SUB_AGENT_TOOLS,
    build_sub_agent_system_prompt,
    get_sub_agent_info,
    list_available_sub_agents,
    resolve_sub_agent_tools,
    run_explore_agent,
    run_general_purpose_agent,
    run_plan_agent,
    run_reviewer_agent,
    run_sub_agent_task,
)

SUB_AGENTS: dict[str, Any] = {
    "explore": explore_agent,
    "plan": plan_agent,
    "reviewer": reviewer_agent,
    "general-purpose": general_purpose_agent,
}


def get_sub_agent(agent_type: str) -> Any | None:
    """获取子智能体实例。"""
    return SUB_AGENTS.get(agent_type)


def get_all_sub_agent_types() -> list[str]:
    """获取所有子智能体类型。"""
    return list(SUB_AGENTS.keys())


__all__ = [
    # 子智能体定义
    "ExploreSubAgent",
    "PlanSubAgent",
    "ReviewerSubAgent",
    "GeneralPurposeSubAgent",
    "explore_agent",
    "plan_agent",
    "reviewer_agent",
    "general_purpose_agent",
    "SUB_AGENTS",
    "get_sub_agent",
    "get_all_sub_agent_types",
    # 运行函数
    "SUB_AGENT_PROMPT_FILES",
    "SUB_AGENT_TOOLS",
    "build_sub_agent_system_prompt",
    "get_sub_agent_info",
    "list_available_sub_agents",
    "resolve_sub_agent_tools",
    "run_explore_agent",
    "run_general_purpose_agent",
    "run_plan_agent",
    "run_reviewer_agent",
    "run_sub_agent_task",
]
