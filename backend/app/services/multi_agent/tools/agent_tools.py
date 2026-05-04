"""Agent tools for multi-agent (workflow and review)."""

import json
from typing import Literal

from langchain_core.tools import tool
from langgraph.config import get_stream_writer
from pydantic import BaseModel, Field

from app.services.multi_agent.prompts import get_tool_description


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


@tool(description=get_tool_description("create_workflow"))
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


class ReviewResult(BaseModel):
    """Review result definition."""

    score: int = Field(description="Document quality score (1-10)", ge=1, le=10)
    feedback: str = Field(description="Review feedback with strengths, issues, and suggestions")


@tool(description=get_tool_description("review_document"))
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
