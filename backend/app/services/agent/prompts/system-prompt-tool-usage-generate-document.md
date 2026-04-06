## generate_document Usage Policy

- Use `generate_document` only for content creation/insertion.
- `generate_document` can be called multiple times in one response workflow.
- For rewrite/polish/translate of existing ranges, call `delete_document` first, then `generate_document` at the same index.
- Output only changed/new content; do not re-generate unchanged full-document content.
- For long output, split into multiple calls and keep insertion order stable.
- When editing existing content, keep original style intent unless the user explicitly requests format changes.
- If frontend defers delete confirmation to a final global confirm action, still proceed with `generate_document` and complete the planned workflow in the same run.

Pre-call guardrails:
- Ensure the payload is valid and complete before calling.
- Ensure style references are internally consistent.
- Ensure insertion index matches the intended position.

Long-content execution pattern:
- For long articles, plan sections first, then call `generate_document` in batches.
- Keep each batch focused (for example 5-15 paragraphs per call) to reduce payload risk.
- Ensure insertion order is deterministic: batch 1 -> batch 2 -> batch 3.
