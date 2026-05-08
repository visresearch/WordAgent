## load_skill_context Usage Policy

Load guidance content from a discovered local skill for the current writing task.

### When to Use
- The task has domain/style constraints and a matching skill likely exists.
- The user explicitly mentions a known skill name or writing standard.
- You need reusable instructions before generating document content.

### Usage
`load_skill_context(skill_name: str)`

- `skill_name`: skill folder name (case-insensitive match is supported by backend).

### After Loading
- Follow the loaded constraints consistently in subsequent reasoning and output.
- If the skill is missing, explain briefly and continue with best-effort defaults.
