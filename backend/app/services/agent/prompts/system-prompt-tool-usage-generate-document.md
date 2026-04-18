## generate_document Usage Policy

- Use `generate_document` only for content creation/insertion.
- `generate_document` can be called multiple times in one response workflow.
- For rewrite/polish/translate of existing ranges, call `delete_document` first, then `generate_document` at the same index.
- Output only changed/new content; do not re-generate unchanged full-document content.
- For long output, split into multiple calls and keep insertion order stable.
- When editing existing content, keep original style intent unless the user explicitly requests format changes.
- If frontend defers delete confirmation to a final global confirm action, still proceed with `generate_document` and complete the planned workflow in the same run.
- For image-generation tasks, do not only return image links in chat text. Build a `generate_document` payload with `document.images` and insert it into the document.
- Keep image URLs unchanged (including query parameters). Do not rewrite or strip URL params.
- Image insertion does not require visible placeholder text; omit placeholder paragraphs unless user explicitly asks.
- If `paraIndex` is not clear, omit it and let backend create empty anchor paragraphs automatically.
- For mixed-language text, split runs and use multiple `rStyle` values; do not use one `rStyle` for the whole document.

Pre-call guardrails:
- Ensure the payload is valid and complete before calling.
- Ensure style references are internally consistent.
- Ensure insertion index matches the intended position.
- Ensure `document.images` entries have usable paths: prefer `url`; if local paths are available, use `tempPath`/`sourcePath`.

Long-content execution pattern:
- For long articles, plan sections first, then call `generate_document` in batches.
- Keep each batch focused (for example 5-15 paragraphs per call) to reduce payload risk.
- Ensure insertion order is deterministic: batch 1 -> batch 2 -> batch 3.

## Detailed article-generation prompt (learned from benchmark JSON)

Use the following strategy when user asks for a formal report/thesis-like article.

### Invocation contract
- Prefer tool execution over plain chat text: after planning, call `generate_document` directly.
- For long content, do not send one oversized payload. Use batched `generate_document` calls.
- Each batch must include:
	- `insertParaIndex`
	- `paragraphs`
	- `tables` (can be `[]`)
	- `images` (can be `[]`)
	- complete `styles` map that covers all referenced style IDs in that batch

### Recommended batch plan
- Batch 1: title page + abstract/intro opening.
- Batch 2..N-1: main chapters (each batch 6-12 paragraphs).
- Final batch: conclusion + references/appendix headings.

### Style profile (benchmark-like)
Use a profile similar to the benchmark sample rather than one-style-for-all output.

- Cover/title level:
	- centered paragraph style with larger line spacing and larger heading fonts.
	- English title run should use Times New Roman.
- Heading hierarchy:
	- chapter heading style (centered or strong heading style)
	- section heading style
	- subsection heading style
- Body:
	- justified
	- first-line indent
	- 1.5 line spacing behavior
- Figure/table caption:
	- centered
	- smaller caption font

### Run-splitting rules (mandatory)
- Do not render whole paragraph with one `rStyle` when mixed content exists.
- Chinese text runs: Chinese font style (for example SimSun/Heiti).
- English words and numbers: Times New Roman style runs.
- Numbering tokens (for example `1.2.3`, `Chapter 2`, `Figure 3-1`) should be split as separate runs when mixed with Chinese.
- If emphasis is needed, add dedicated bold run styles instead of overriding entire paragraph style.

### Paragraph construction rules
- Never use `\n` inside `run.text`.
- One visual line = one paragraph item.
- Blank lines use empty paragraph object: `{ "pStyle": "", "runs": [] }`.

### Image insertion rules
- Prefer `document.images` with `url`/`tempPath`.
- No visible placeholder text required.
- If exact `paraIndex` is unclear, omit it and let backend append empty anchor paragraphs.

### Suggested execution prompt (internal)
Before calling `generate_document`, follow this checklist:
1. Confirm target structure (title/chapter/section/subsection/body).
2. Build style map first (paragraph + run styles for hierarchy and mixed language).
3. Draft paragraphs with explicit run splitting for Chinese vs English/numbers.
4. Validate all referenced styles exist.
5. Execute `generate_document` in deterministic batches.
