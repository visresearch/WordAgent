Generate formatted content and insert it into the Word document.

## Parameters
- `document` (object): raw `DocumentOutput` object. Do not pass escaped JSON, a string, or `{"document": {...}}` inside this value.
- `insertParaIndex` (int): insert before this 0-based paragraph index. `-1` appends.
- `docId` (string/int, optional): target document ID; omit for the active document.

## Required payload shape
- Top-level tool args: `{"document": {...}, "insertParaIndex": -1}`.
- `document` should include `paragraphs`, `tables` (can be `[]`), and `styles`.
- Every referenced `pStyle/rStyle/cStyle/tStyle` must exist in `styles`.
- Never put `\n` inside `run.text`; one visual line is one paragraph.
- Blank line: `{ "pStyle": "", "runs": [] }`.

## Use
- New writing, append/insert content, or replacement content after `delete_document`.
- Long output: split into ordered batches (roughly 5-15 paragraphs each).
- Delete-only tasks: do not call this tool.

## Runs and images
- Text run: `{ "text": "...", "rStyle": "rS_2" }`.
- Image run: `{ "url": "...", "width": 320, "height": 240, "altText": "..." }` (no `text` field).
- Keep image URLs unchanged, including query parameters. `url` may be http/https, file URL, or local/project-relative path.
- Keep image aspect ratio; omit `width`/`height` to use native size.

## Index drift with `delete_document`
`generate_document` inserts before `insertParaIndex`. Paragraphs at that index and after move to higher indices. If you inserted above content you later plan to delete, call `read_document` or `search_documnet` before `delete_document` and use the updated indices.

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
	"insertParaIndex": -1
}
```
