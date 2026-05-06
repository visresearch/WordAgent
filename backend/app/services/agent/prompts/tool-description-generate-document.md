# ⚠️ MOST CRITICAL: Tool Call Format Rule

**When calling `generate_document`, the `document` parameter MUST be a direct JSON object, NOT a JSON string!**

- ✅ CORRECT: `{"document": {"paragraphs": [...], "styles": {...}}, "insertParaIndex": -1}`
- ❌ WRONG: `{"document": "{\"paragraphs\": [...]}"}` (escaped string inside string!)
- ❌ WRONG: `{"document": {"document": {...}}}` (double-wrapped)
- ❌ WRONG: `generate_document(document="...")` (document passed as string argument)

**NEVER use `json.dumps()`, `JSON.stringify()`, escape quotes, wrap in quotes, or call str() on JSON.**

The `document` parameter must be passed as a raw JSON object, like calling a function with a Python dict literal.

**`insertParaIndex` must be passed as a separate tool argument, not inside the document object!**

---

Generate formatted document payload for insertion into a Word document.

## Parameters:
- `document` (object, DocumentOutput): generated content payload for insertion (paragraphs/tables/styles).
- `docId` (string, optional): Document ID to insert into. If None, uses the currently active document. The documentId for each open document is included in the documentMeta sent with each chat message.
- `insertParaIndex` (int, optional): 0-based paragraph index where content will be inserted before. Default is -1 (append to end). Use 0 for beginning of document.

## When to use:
- Create new content and insert into document.
- Insert replacement content immediately after delete flow.
- Continue replacement flow even when delete confirmation is deferred on frontend.
- Generate long articles by splitting content into multiple `generate_document` calls.

## When not to use:
- You only need to read/search/analyze without writing changes.
- User explicitly asks for delete-only operation.

## Returns:
- `dict`: echoed generated document object.

## Image Payload Rules:
- Images are inline runs inside paragraphs. A run without `text` field is an image.
- Text run: `{"text": "...", "rStyle": "rS_1"}`
- Image run: `{"url": "...", "width": 320, "height": 240, "altText": "..."}` (no text field)
- Keep image URL unchanged (including query parameters). Do not strip URL params.
- Image runs can be mixed with text runs in the same paragraph.
- Recommend `pStyle` centered with zero left/right indent, for example `["center", 0, 0, 0, 0, 0, 0, "正文", 1]`.
- Keep image width within printable page width; if uncertain, use moderate width (320-420) or omit explicit width.

## Typography rules for runs:
- Do not use one `rStyle` for the entire document.
- Split mixed text into multiple runs when needed.
- Chinese body text should use a Chinese body style (for example `rS_2`/SimSun).
- English words and numbers should use a Times New Roman run style (for example `rS_4` in body, `rS_3` in headings).
- Do not insert extra spaces around English/number runs only to separate them from adjacent Chinese text.

## Figure/Chart caption rules:
- If a figure/chart is generated, add one caption paragraph directly below it.
- Caption format: `图X，<brief description>`.
- Caption paragraph should use `pS_6` (centered, style name `题图`).
- Caption run should use a dedicated bold black-5th-size style (for example `rS_5`: `"黑体", 10.5`).

## JSON construction examples:

Minimal append payload:
```json
{
	"document": {
		"paragraphs": [
			{
				"pStyle": "pS_3",
				"runs": [{ "text": "这是新增段落。", "rStyle": "rS_2" }]
			}
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

Replacement payload at a fixed index:
```json
{
	"document": {
		"paragraphs": [
			{
				"pStyle": "pS_3",
				"runs": [{ "text": "这是重写后的第 1 段。", "rStyle": "rS_2" }]
			},
			{
				"pStyle": "pS_3",
				"runs": [{ "text": "这是重写后的第 2 段。", "rStyle": "rS_2" }]
			}
		],
		"tables": [],
		"styles": {
			"pS_3": ["justify", 0, 0, 0, 24, 0, 0, "正文", 1],
			"rS_2": ["宋体", 12, false, false, 0, "#000000", "#000000", 0, false, false, false]
		}
	},
	"insertParaIndex": 12
}
```

Image insertion payload:
```json
{
	"document": {
		"paragraphs": [
			{
				"pStyle": "pS_3",
				"runs": [
					{ "text": "以下是一张示例图片：", "rStyle": "rS_2" },
					{ "url": "https://example.com/demo.png?Expires=123&Signature=abc", "width": 320, "height": 240, "altText": "示意图" },
					{ "text": "，请参考。", "rStyle": "rS_2" }
				]
			}
		],
		"tables": [],
		"styles": {
			"pS_3": ["center", 0, 0, 0, 0, 0, 0, "正文", 1],
			"rS_2": ["宋体", 12, false, false, 0, "#000000", "#000000", 0, false, false, false]
		}
	},
	"insertParaIndex": -1
}
```

## Examples (scenarios):
- User says: "在文末新增一段项目总结" -> call `generate_document` to append the new paragraph block.
- User says: "把第 12-15 段重写为商务语气" -> call `delete_document` for old range, then `generate_document` at the same insertion position.
- User says: "生成一份报告" / "写一篇关于XX的文章" -> ONLY call `generate_document`, NOT `delete_document`.
- Frontend uses one final confirm button for pending deletes -> still call `generate_document` in the same run; do not end early waiting for delete confirmation.
- User asks for a long report (for example 40+ paragraphs) -> call `generate_document` multiple times in ordered batches instead of one oversized payload.

## Detailed prompting template for article generation (sample-style)

Use this template when user asks to generate a formal article/report:

```text
You are writing a formal Chinese academic-style article and must output via generate_document.

Hard requirements:
1) Call generate_document (not plain text-only answer) for actual document output.
2) For long content, split into multiple generate_document calls (6-12 paragraphs per batch).
3) Include a complete styles map in every call that covers all pStyle/rStyle/cStyle/tStyle references.
4) Never use \n in run.text. One line = one paragraph object.
5) Use empty paragraph objects for blank lines: {"pStyle":"","runs":[]}.
6) Avoid consecutive empty paragraphs; keep at most one blank line unless user explicitly requires more.
7) REMEMBER: document parameter must be a JSON object, NOT a string with escaped JSON! Do NOT double-wrap with `{"document": {...}}` structure — pass the document object directly as the argument value.

Style strategy (learned from benchmark document):
- Keep a strict hierarchy: title -> chapter -> section -> subsection -> body.
- Body paragraph should be justified with first-line indent and 1.5 spacing behavior.
- Do run-level mixed typography:
	- Chinese runs -> Chinese body font style.
	- English words and numbers -> Times New Roman run style.
	- Do not add extra spaces around English/number runs when adjacent to Chinese.
	- Do not use one rStyle from start to end.

Image strategy:
- Images are inline runs inside paragraphs. A run without `text` field is an image.
- Example: `{"url": "...", "width": 320, "height": 240, "altText": "..."}`
- Image runs can be mixed with text runs in the same paragraph.
- Prefer `pStyle` centered and left/right indent = 0.
- Ensure image width is not larger than printable page width.
- If there is a figure/chart, add a caption paragraph directly below it using `图X，描述`, with `pS_6` (centered, `题图`) and a dedicated caption run style (`rS_5`, 黑体五号).

Output process:
Step A: build style map for this batch.
Step B: draft paragraphs with explicit run splitting.
Step C: validate style references.
Step D: call generate_document.
```
