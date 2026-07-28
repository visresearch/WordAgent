Generate formatted content and insert it into the Word document.

## Parameters
- `document` (object): raw `DocumentOutput` object. Do not pass escaped JSON, a string, or `{"document": {...}}` inside this value.
- `insertParaID` (int, required): insertion anchor. Use `0` to insert at the document start in either an empty or non-empty document. Use an existing nonzero paragraph ID to insert after that paragraph.
- `docId` (int, optional): target document ID; use `0` for the active document.

## Required payload shape
- Top-level tool args: `{"document": {...}, "insertParaID": 123456}`.
- The tool args must be exactly one balanced top-level JSON object. Do not add extra closing braces/brackets after `docId` or after the top-level object.
- `document` should include `paragraphs`, `tables` (can be `[]`), and `styles`.
- Every referenced `pStyle/rStyle/cStyle/tStyle` must exist in `styles`.
- Style arrays must be complete: `pS_*` has 9 items, `rS_*` has 11 items, `cS_*` has 4 items, `tS_*` has 1 item.
- Non-empty paragraphs must use a non-empty paragraph style ID such as `pS_3`, and that ID must be defined in `styles`.
- Use `pStyle: ""` only for a truly blank line with `runs: []`; never use empty `pStyle` for paragraphs that contain text or images.
- Text runs must use an `rStyle` such as `rS_2`, and that ID must be defined in `styles`.
- English text in body paragraphs must use a run style whose font is `Times New Roman`; split mixed Chinese-English text into separate runs and preserve the specified Chinese font for Chinese runs.
- Never put `\n` inside `run.text`; one visual line is one paragraph.
- In `run.text`, `cell.text`, and table paragraph text, never use raw ASCII double quote characters (`"`). For quoted phrases, use Chinese quotation marks such as `“三夏”` or `「三夏」`. Raw `"` in text often breaks tool-call JSON.
- Blank line: `{ "pStyle": "", "runs": [] }`.
- `insertParaID` is mandatory. Never omit it and never pass `null`/`None`.
- For non-empty documents, use `0` for the document start or an existing paragraph ID from selected context, `read_document`, or `search_document`; do not guess nonzero IDs.
- If document metadata says `isEmpty=true` or `read_document` returns only one empty placeholder paragraph such as `runs: []`, treat the document as blank and use `"insertParaID": 0`.

## Use
- New writing, append/insert content, or replacement content after `delete_document`.
- Long output: split into ordered batches (roughly 5-15 paragraphs each).
- Delete-only tasks: do not call this tool.

## Return value
- On successful frontend insertion, `lastParagraph` contains the final physical paragraph created by this call: `paraID`, zero-based `paraIndex`, `pageStart`, and `pageEnd`.
- `lastParagraph.paraID` is the authoritative continuation anchor. Use it as the next `insertParaID` when appending immediately after this generated block; do not guess another trailing blank paragraph.
- WPS returns physical page numbers. Microsoft Word returns `pageStart/pageEnd` as `null` when its API cannot determine them reliably.
- If the return contains a timeout warning, do not repeat the call because the content may already exist. Use `read_document` to recover the actual ending location.

## Runs and images
- Text run: `{ "text": "...", "rStyle": "rS_2" }`.
- A paragraph containing this run must also have a defined `pStyle`, for example `{ "pStyle": "pS_3", "runs": [{ "text": "...", "rStyle": "rS_2" }] }`.
- If text includes a quoted phrase, write it as `“quoted text”` / `「quoted text」`, not `"quoted text"`.
- Image run: `{ "url": "...", "width": 320, "height": 240, "altText": "..." }` (no `text` field).
- Keep image URLs unchanged, including query parameters. `url` may be http/https, file URL, or local/project-relative path.
- Keep image aspect ratio; omit `width`/`height` to use native size.

## ParaID stability with `delete_document`
Prefer paraID-based workflows: search/read returns paragraph IDs and delete uses paraIDs directly. This avoids index drift after insertion.

## Pre-call checklist
Before calling `generate_document`, scan the payload:
- Collect every `pStyle`, `rStyle`, `cStyle`, and `tStyle` value that appears in paragraphs, runs, cells, and tables.
- Confirm each collected non-empty style ID exists as a key in `document.styles`.
- Confirm no paragraph with `runs` uses `pStyle: ""`.
- Confirm blank lines are exactly `{ "pStyle": "", "runs": [] }`.

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

## Blank document first write
If document metadata says the active document is empty, e.g. `{"documentId":1265989210,"isEmpty":true,"totalParas":1}`, the first write must use `"insertParaID": 0` and target the active document:

```json
{
	"document": {
		"paragraphs": [
			{ "pStyle": "pS_1", "runs": [{ "text": "标题", "rStyle": "rS_1" }] }
		],
		"tables": [],
		"styles": {
			"pS_1": ["center", 0, 0, 0, 0, 12, 6, "标题", 1],
			"rS_1": ["黑体", 16, true, false, 0, "#000000", "#000000", 0, false, false, false]
		}
	},
	"insertParaID": 0,
	"docId": 1265989210
}
```
