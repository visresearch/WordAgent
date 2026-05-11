Create a multi-agent workflow for task execution.

## Parameters
- `workflow` (object): Workflow definition with:
  - `summary`: Brief description of the entire plan
  - `steps`: Array of WorkflowStep objects

## WorkflowStep Structure
```json
{
  "agent": "research|outline|writer|reviewer",
  "task": "Specific task description for this step",
  "depends_on": [0, 1]
}
```

## Available Agents
- `research`: Search web for reference information
- `outline`: Read documents and generate outlines
- `writer`: Generate Word documents
- `reviewer`: Review document quality

## When to Use
- User request requires multiple steps to complete
- Task involves research, outline, writing, and review
- Simple Q&A does not need workflow

## Example
```json
{
  "summary": "Research topic, create outline, write document",
  "steps": [
    {"agent": "research", "task": "Search for recent developments in AI", "depends_on": []},
    {"agent": "outline", "task": "Generate outline based on research", "depends_on": [0]},
    {"agent": "writer", "task": "Write document using outline and research", "depends_on": [1]}
  ]
}
```

## Rules
- MUST call `create_workflow` tool for workflow output
- Do NOT output workflow as plain text
- Task descriptions must be specific and actionable
- Set `depends_on` correctly for data flow
