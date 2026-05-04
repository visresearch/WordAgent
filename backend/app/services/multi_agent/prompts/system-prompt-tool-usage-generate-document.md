## generate_document Usage Policy

- Use `generate_document` only for content creation/insertion.
- `generate_document` can be called multiple times in one response workflow.
- For rewrite/polish/translate of existing ranges, call `delete_document` first, then `generate_document` at the same index.
- Output only changed/new content; do not re-generate unchanged full-document content.
- When editing existing content, keep original style intent unless the user explicitly requests format changes.
- If frontend defers delete confirmation to a final global confirm action, still proceed with `generate_document` and complete the planned workflow in the same run.

Pre-call guardrails:
- Ensure the payload is valid and complete before calling.
- Ensure style references are internally consistent.
- Ensure insertion index matches the intended position.
- Image runs: `{"url": "...", "width": 320, "height": 240}`. Prefer `pStyle` centered with zero horizontal indent.

## Long-content Batching Strategy

**When to batch** (only split into multiple calls):
- Document has 30+ paragraphs
- Payload would exceed ~200KB

**Batch plan**:
1. Batch 1: Title + Abstract/Introduction (5-10 paragraphs)
2. Batch 2..N-1: Main chapters (6-12 paragraphs each)
3. Final batch: Conclusion + References (5-10 paragraphs)

**insertParaIndex values**:
- `0`: Replace entire document (use for first batch)
- `-1`: Append after last paragraph (use for subsequent batches)

**Critical rules**:
- Each batch must include complete `styles` map
- Each batch must have proper `insertParaIndex`
- Never write the same content twice
- Keep insertion order deterministic: batch 1 → batch 2 → batch 3

**Wrong** (duplicate content):
```
Call 1: insertParaIndex: -1, paragraphs: [Title, Intro, Section 1]
Call 2: insertParaIndex: -1, paragraphs: [Intro, Section 1, Section 2]  ← DUPLICATE!
```

**Correct** (non-overlapping):
```
Call 1: insertParaIndex: 0,  paragraphs: [Title, Intro, Section 1]
Call 2: insertParaIndex: -1, paragraphs: [Section 2, Section 3]
Call 3: insertParaIndex: -1, paragraphs: [Section 4, Conclusion]
```

## Key format rules
- `document` is a JSON object: `{"document": {"insertParaIndex": 0, "paragraphs": [...], "styles": {...}}}`
- Never use `\n` inside `run.text`. One visual line = one paragraph.
- Blank lines use empty paragraph: `{"pStyle": "", "runs": []}`
- Each table cell needs `cStyle` and `tStyle`.
- No `null` in style arrays.

See `system-prompt-default-recommend-document-style.md` for complete style guide.
