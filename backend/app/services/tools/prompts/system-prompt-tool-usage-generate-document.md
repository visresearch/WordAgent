## generate_document Usage Policy

- Use for content creation/insertion; do not use for delete-only or analysis-only tasks.
- For rewrite/polish/translate: `read_document` if needed, `delete_document` old range, then `generate_document` replacement at the same index.
- Output only changed/new content; never re-generate unchanged full documents.
- Long output: split into ordered batches and keep insertion order deterministic.
- Keep original style intent unless the user asks for formatting changes.
- Validate before calling: raw object payload, complete `styles`, valid style references, correct `insertParaID`.
- The tool call arguments must be one balanced JSON object. Do not add an extra `}` or `]` after the final field.
- Style reference closure is mandatory: every non-empty `pStyle`, `rStyle`, `cStyle`, and `tStyle` used anywhere in the payload must exist as a key in `document.styles`.
- Never use `pStyle: ""` for paragraphs containing text or images. Empty `pStyle` is only valid for a blank paragraph with `runs: []`.
- For ordinary body paragraphs, use `pS_3` with `rS_2` unless the requested format requires another defined style.
- JSON safety: inside generated document text fields (`run.text`, table `cell.text`, table paragraph text), do not use raw ASCII double quote characters (`"`). Use Chinese quotation marks such as `“...”` or `「...」` for quoted phrases.
- `insertParaID` is required. Never omit it and never pass `null`/`None`.
- For non-empty documents, `insertParaID` must come from selected context or a real paragraph ID returned by `read_document`/`search_documnet`; do not invent IDs.
- Use `insertParaID: 0` only for the first write into an empty/new document; it means insert at the document start.
- Images must be inline runs with a single `url`; keep URLs unchanged and preserve aspect ratio.
- If paragraph location is uncertain, re-read/search and use paragraph IDs for follow-up delete operations.
- If deletes are confirmed later by the frontend, continue the full planned workflow; do not wait for per-delete confirmation.
