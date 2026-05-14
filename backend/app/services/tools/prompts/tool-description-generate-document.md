Generate formatted content and insert it into the Word document.

## Parameters
- `document` (object): raw `DocumentOutput` object. Do not pass escaped JSON, a string, or `{"document": {...}}` inside this value.
- `insertParaID` (int, optional): insert after this paragraph ID. Omit for current cursor position.
- `docId` (int, optional): target document ID; use `0` for the active document.

## Required payload shape
- Top-level tool args: `{"document": {...}, "insertParaID": 123456}`.
- `document` should include `paragraphs`, `tables` (can be `[]`), and `styles`.
- Every referenced `pStyle/rStyle/cStyle/tStyle` must exist in `styles`.
- Never put `\n` inside `run.text`; one visual line is one paragraph.
- Blank line: `{ "pStyle": "", "runs": [] }`.
- `insertParaID` must be an existing paragraph ID from recent `read_document`/`search_documnet` results; do not guess IDs.

## Use
- New writing, append/insert content, or replacement content after `delete_document`.
- Long output: split into ordered batches (roughly 5-15 paragraphs each).
- Delete-only tasks: do not call this tool.

## Runs and images
- Text run: `{ "text": "...", "rStyle": "rS_2" }`.
- Image run: `{ "url": "...", "width": 320, "height": 240, "altText": "..." }` (no `text` field).
- Keep image URLs unchanged, including query parameters. `url` may be http/https, file URL, or local/project-relative path.
- Keep image aspect ratio; omit `width`/`height` to use native size.

## ParaID stability with `delete_document`
Prefer paraID-based workflows: search/read returns paragraph IDs and delete uses paraIDs directly. This avoids index drift after insertion.

## Minimal example
```json
{
	"document": {
		"paragraphs": [
			{ "pStyle": "pS_3", "runs": [{ "text": "这是新增段落。", "rStyle": "rS_2" }] }
		],
		"tables": [],
		"styles": {
			"pS_3": ["justify", 0, 0, 0, 24, 0, 0, "正文", 1],
			"rS_2": ["宋体", 12, false, false, 0, "#000000", "#000000", 0, false, false, false]
		}
	},
	"insertParaID": 123456
}
```
