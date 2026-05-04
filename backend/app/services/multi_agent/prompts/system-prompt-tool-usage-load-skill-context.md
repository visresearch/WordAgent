## load_skill_context

Load guidance content from a discovered local skill for the current writing task.

### When to Use
- Writing task involves specific domains or formats (formal reports, technical documentation)
- User mentions a specific skill or writing style
- Need guidance on writing standards for a particular field

### Usage
```
load_skill_context(skill_name: str)
```
- `skill_name`: The folder name of the skill to load (case-insensitive)

### After Loading
- Follow the skill's writing constraints and guidelines
- Keep output consistent with the skill rules
