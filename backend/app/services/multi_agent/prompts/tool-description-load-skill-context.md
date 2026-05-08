Load guidance content from a discovered skill by folder name.

## Signature
`load_skill_context(skill_name: str) -> str`

## Use cases
- Load reusable skill instructions before planning or execution.
- Reuse project-specific best practices without copying full skill files.

## Notes
- `skill_name` should be the skill folder name (not a file path).
