Create and execute a sub-agent task for specialized work.

## Parameters

- `description` (str): Short task title shown in status messages.
- `prompt` (str): Detailed task instructions for the sub-agent.
- `agent_type` (str): One of:
  - `"explore"`: Search and analyze document content, find specific information
  - `"plan"`: Design implementation approach, break down complex tasks
  - `"reviewer"`: Review content quality, provide actionable suggestions
  - `"general-purpose"`: Multi-step complex tasks requiring various tools

## When to Use

- `explore`: Before writing from multiple sources, extract structure and key facts
- `plan`: For complex multi-step tasks, design approach before implementation
- `reviewer`: After draft is complete, check quality and consistency
- `general-purpose`: When task requires read + search + generate + delete combination

## When Not to Use

- Main writing/editing actions (use main agent document tools)
- Simple tasks that don't need delegated analysis/review
- Empty documents (continue directly with main agent)

## Returns

- `str`: Sub-agent response text or completion summary

## Examples

Explore task - analyze reference documents:
```json
{
  "description": "分析参考文档结构",
  "prompt": "阅读上传材料，提取目录结构、核心观点和可复用表达。",
  "agent_type": "explore"
}
```

Plan task - design implementation approach:
```json
{
  "description": "设计文档大纲",
  "prompt": "根据用户需求，设计文档结构和大纲，确定各章节内容要点。",
  "agent_type": "plan"
}
```

Reviewer task - quality review:
```json
{
  "description": "终稿质量审阅",
  "prompt": "检查语病、术语一致性和逻辑跳跃，给出可执行修改建议。",
  "agent_type": "reviewer"
}
```

General-purpose task - complex multi-step work:
```json
{
  "description": "综合分析报告",
  "prompt": "搜索相关资料，阅读关键章节，生成综合分析报告。",
  "agent_type": "general-purpose"
}
```
