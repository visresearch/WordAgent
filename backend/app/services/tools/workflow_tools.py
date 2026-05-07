"""多智能体编排工具（仅 multi_agent 模式使用）。

- `create_workflow`: planner agent 用来产出整体步骤拆解
- `review_document`: reviewer agent 用来提交评审结论

实现通过工厂函数装配，由 `multi_agent/tools.py` 入口注入 prompt description。
"""

from __future__ import annotations

import json
from typing import Literal

from langchain_core.tools import tool
from langgraph.config import get_stream_writer
from pydantic import BaseModel, Field


class WorkflowStep(BaseModel):
    """Workflow step definition."""

    agent: Literal["research", "outline", "writer", "reviewer"] = Field(description="The agent to execute this step")
    task: str = Field(description="Specific task description for this step")
    depends_on: list[int] = Field(
        default_factory=list,
        description="Indices of steps this step depends on (0-based)",
    )


class Workflow(BaseModel):
    """Workflow definition."""

    steps: list[WorkflowStep] = Field(description="Ordered list of workflow steps")
    summary: str = Field(description="Brief summary of the entire plan")


class ReviewResult(BaseModel):
    """Review result definition."""

    score: int = Field(description="Document quality score (1-10)", ge=1, le=10)
    feedback: str = Field(description="Review feedback with strengths, issues, and suggestions")


def build_create_workflow(description: str):
    """构造 create_workflow 工具实例。"""

    @tool(description=description)
    def create_workflow(workflow: Workflow) -> str:
        """Create a multi-agent workflow for task execution."""
        writer = get_stream_writer()
        wf_dict = workflow.model_dump()
        step_count = len(wf_dict.get("steps", []))
        summary = wf_dict.get("summary", "")
        print(f"[create_workflow] Workflow: {summary}, {step_count} steps")
        if writer:
            writer({"type": "status", "content": f"📋 工作流已规划（{step_count} 个步骤）: {summary}"})
        return json.dumps(wf_dict, ensure_ascii=False)

    return create_workflow


def build_review_document(description: str):
    """构造 review_document 工具实例。"""

    @tool(description=description)
    def review_document(review: ReviewResult) -> str:
        """Submit document review results with score and feedback."""
        writer = get_stream_writer()
        review_dict = review.model_dump()
        score = review_dict.get("score", 0)
        feedback = review_dict.get("feedback", "")[:100]
        print(f"[review_document] Score: {score}/10")
        if writer:
            writer(
                {
                    "type": "status",
                    "content": f"📝 审核评分: {score}/10 - {feedback}...",
                }
            )
        return json.dumps(review_dict, ensure_ascii=False)

    return review_document


__all__ = [
    "WorkflowStep",
    "Workflow",
    "ReviewResult",
    "build_create_workflow",
    "build_review_document",
]
