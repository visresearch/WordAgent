Create a sub-agent for focused analysis, planning, or review.

## Parameters
- `description` (str): short task title.
- `prompt` (str): specific instructions and expected output.
- `agent_type` (str): `explore`, `plan`, `reviewer`, or `general-purpose`.

## Use
- `explore`: extract facts/structure from long or multiple sources.
- `plan`: design an approach for complex tasks.
- `reviewer`: review a completed draft.
- `general-purpose`: delegated multi-step analysis.

## Do not use
- For direct document writing/editing; main agent should call document tools.
- For simple tasks or empty documents.
