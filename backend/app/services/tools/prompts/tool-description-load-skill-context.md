Load guidance content from a discovered local skill by folder name.

## Signature
`load_skill_context(skill_name: str) -> str`

## Use cases
- Load reusable writing constraints before generating or revising content.
- Reuse project/domain-specific style guidance from installed skills.

## Notes
- `skill_name` should be the skill folder name (not a file path).
