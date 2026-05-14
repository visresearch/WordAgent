## generate_document Usage Policy

- Use for content creation/insertion; do not use for delete-only or analysis-only tasks.
- For rewrite/polish/translate: `read_document` if needed, `delete_document` old range, then `generate_document` replacement at the same index.
- Output only changed/new content; never re-generate unchanged full documents.
- Long output: split into ordered batches and keep insertion order deterministic.
- Keep original style intent unless the user asks for formatting changes.
- Validate before calling: raw object payload, complete `styles`, valid style references, correct `insertParaID`.
- `insertParaID` must come from a real paragraph ID returned by `read_document`/`search_documnet`; do not invent IDs.
- Images must be inline runs with a single `url`; keep URLs unchanged and preserve aspect ratio.
- If paragraph location is uncertain, re-read/search and use paragraph IDs for follow-up delete operations.
- If deletes are confirmed later by the frontend, continue the full planned workflow; do not wait for per-delete confirmation.
