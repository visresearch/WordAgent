Create and execute a sub-agent task.

## Parameters:
- `description` (str): short task title shown in status events.
- `prompt` (str): detailed task instruction text for the sub-agent.
- `agent_type` (str): one of:
	- `"reviewer"`: review-oriented sub-agent.
	- `"explorer"`: analysis-oriented sub-agent.

## When to use:
- `explorer`: analyze long/complex sources before writing.
- `reviewer`: review already-generated draft quality.

## When not to use:
- Main writing/editing actions (should be done by main agent document tools).
- Simple tasks that do not need delegated analysis/review.

## Returns:
- `str`: final sub-agent response text (or summarized completion text).

## JSON construction examples:

Explorer task:
```json
{
	"description": "分析参考文档结构",
	"prompt": "阅读上传材料，提取目录结构、核心观点和可复用表达。",
	"agent_type": "explorer"
}
```

Reviewer task:
```json
{
	"description": "终稿质量审阅",
	"prompt": "检查语病、术语一致性和逻辑跳跃，给出可执行修改建议。",
	"agent_type": "reviewer"
}
```

## Examples (scenarios):
- Before drafting from multiple reference files, call `run_sub_agent` with `explorer` to extract structure and key facts.
- After final draft generation, call `run_sub_agent` with `reviewer` to identify wording issues and consistency problems.