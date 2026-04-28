## run_sub_agent Usage Policy

Use `run_sub_agent` to delegate specialized tasks to focused sub-agents. Choose the right agent type based on the task.

### Agent Types

| Agent | When to Use |
|-------|--------------|
| `explore` | Analyze document structure, find specific content, extract key information |
| `plan` | Design implementation approach, break down complex tasks into steps |
| `reviewer` | Review generated content, provide actionable improvement suggestions |
| `general-purpose` | Multi-step complex tasks requiring various tools |

### Guidelines

- **Use sub-agents for focused, specialized work** — don't overload main agent with everything
- **Keep document writing/editing in main agent** — sub-agents are for analysis, planning, and review
- **For long/complex sources**: Use `explore` first to understand structure before writing
- **For multi-step tasks**: Use `plan` to design approach, then execute with main agent
- **For quality assurance**: Use `reviewer` after draft is complete
- **Skip `explore` on empty documents**: If totalParas <= 1 and no explicit source ranges, continue directly

### Recommended Workflow

1. **Explore** → Analyze source documents and structure
2. **Plan** → Design implementation approach (optional, for complex tasks)
3. **Main Agent** → Write and modify documents using document tools
4. **Reviewer** → Final quality check and improvement suggestions
