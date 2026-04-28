"""主智能体调用子智能体的工具。"""

import json
from typing import Literal

from langchain_core.tools import tool

from app.services.agent.prompts import get_tool_description
from app.services.agent.tools.callback import _current_request_context


# ---------------------------------------------------------------------------
# 工具定义
# ---------------------------------------------------------------------------


@tool(description=get_tool_description("run_sub_agent"))
def run_sub_agent(
    description: str,
    prompt: str,
    agent_type: Literal["reviewer", "explore", "plan", "general-purpose"] = "reviewer",
) -> str:
    """创建并运行子智能体来完成专项任务。

    可用的子智能体类型：
    - reviewer: 专业文档评审专家，提供修改建议
    - explore: 文档搜索和探索专家，快速定位内容
    - plan: 架构师和规划专家，设计实现方案
    - general-purpose: 通用目的智能体，执行复杂任务
    """
    # 延迟导入避免循环依赖
    from app.services.agent.subAgents import run_sub_agent_task

    context = _current_request_context.get(None) or {}
    document_meta = context.get("document_meta") if isinstance(context, dict) else None
    document_range = context.get("document_range") if isinstance(context, dict) else None

    # 文档明确为空时，避免无意义地启动 explore
    if agent_type == "explore" and isinstance(document_meta, dict):
        total_paras = document_meta.get("totalParas")
        try:
            total_paras = int(total_paras)
        except (TypeError, ValueError):
            total_paras = None
        has_ranges = isinstance(document_range, list) and len(document_range) > 0
        if total_paras is not None and total_paras <= 1 and not has_ranges:
            return (
                "Skipped explore sub-agent: document is empty (totalParas<=1 and no document ranges). "
                "Please proceed directly in main agent or provide concrete source ranges/files."
            )

    context_lines: list[str] = []
    if isinstance(document_meta, dict) and document_meta:
        context_lines.append("[Document Global Metadata]")
        context_lines.append(json.dumps(document_meta, ensure_ascii=False))
    if isinstance(document_range, list) and document_range:
        context_lines.append("[Document Ranges]")
        context_lines.append(json.dumps(document_range, ensure_ascii=False))

    sub_prompt = prompt
    if context_lines:
        context_block = "\n".join(context_lines)
        sub_prompt = (
            f"{prompt}\n\nThe following context is injected by main agent runtime; use it if relevant:\n{context_block}"
        )

    return run_sub_agent_task(
        description=description,
        prompt=sub_prompt,
        agent_type=agent_type,
    )
