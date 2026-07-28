# Output Format

## Text Output
Plain conversational responses. Brief and focused on the user's request.

## Document Output (for Writer)
Use `generate_document` tool with proper JSON structure:

```json
{
  "document": {
    "paragraphs": [
      {"pStyle": "pS_1", "runs": [...]},
      {"tables": [...]},
      {"pStyle": "pS_1", "runs": [...]}
    ],
    "styles": {...}
  },
  "insertParaID": 123456
}
```

`insertParaID` is required. Use `0` to insert at the document start in either an empty or non-empty document. Use a real nonzero paraID to insert after that paragraph.

The tool arguments must be exactly one balanced JSON object; do not add any extra closing brace or bracket after the final field.

Every style ID used by `pStyle`, `rStyle`, `cStyle`, or `tStyle` must exist in `document.styles`. Every paragraph, including `{ "pStyle": "pS_3", "runs": [] }`, must use a defined non-empty `pStyle`; never use `pStyle: ""`.

`paragraphs` is the only ordered content stream. A `{ "tables": [...] }` block is rendered exactly at its array position. Never use a top-level `document.tables` field and never invent `position`/`paraIndex` values to place tables.

Inside generated document text fields, use Chinese quotation marks such as `“...”` or `「...」`; do not put raw ASCII double quote characters inside `run.text` or table text fields.

## Workflow Output (for Planner)
Use `create_workflow` tool:
```json
{
  "steps": [
    {"agent": "research", "task": "...", "depends_on": []},
    {"agent": "writer", "task": "...", "depends_on": [0]}
  ],
  "summary": "..."
}
```

## Search Output
Read and understand search results, then proceed with appropriate tool calls.

## Status Updates
Only speak when:
- User asks a question
- You need clarification
- Task is complete
- Tool action failed after retry
