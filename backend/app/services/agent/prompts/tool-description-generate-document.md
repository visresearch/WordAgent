Generate formatted document payload for insertion into the active Word document.

## Parameters:
- `document` (object, DocumentOutput): generated content payload for insertion (paragraphs/tables/images/styles/insert index).

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
- To insert images into Word, put image objects in `document.images`.
- Use URL field for generated images: `{"url": "https://...png?token=..."}`.
- Do not modify URL query parameters.
- No visible placeholder text is required.
- If you provide `paraIndex`, align it to an existing paragraph index in this payload.
- If unsure, you can omit `paraIndex`; backend will auto-append empty anchor paragraphs for image insertion.

## Typography rules for runs:
- Do not use one `rStyle` for the entire document.
- Split mixed text into multiple runs when needed.
- Chinese body text should use a Chinese body style (for example `rS_2`/SimSun).
- English words and numbers should use a Times New Roman run style (for example `rS_4` in body, `rS_3` in headings).

## JSON construction examples:

Minimal append payload:
```json
{
	"document": {
		"insertParaIndex": -1,
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
	}
}
```

Replacement payload at a fixed index:
```json
{
	"document": {
		"insertParaIndex": 12,
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
	}
}
```

Image insertion payload:
```json
{
	"document": {
		"insertParaIndex": -1,
		"paragraphs": [],
		"tables": [],
		"images": [
			{
				"type": "inline",
				"url": "https://example.com/demo.png?Expires=123&Signature=abc",
				"width": 320,
				"height": 240,
				"altText": "示意图"
			}
		],
		"styles": {
			"pS_3": ["center", 0, 0, 0, 0, 0, 0, "正文", 1],
			"rS_2": ["宋体", 12, false, false, 0, "#000000", "#000000", 0, false, false, false]
		}
	}
}
```

## Examples (scenarios):
- User says: “在文末新增一段项目总结” -> call `generate_document` to append the new paragraph block.
- User says: “把第 12-15 段重写为商务语气” -> call `delete_document` for old range, then `generate_document` at the same insertion position.
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

Style strategy (learned from benchmark document):
- Keep a strict hierarchy: title -> chapter -> section -> subsection -> body.
- Body paragraph should be justified with first-line indent and 1.5 spacing behavior.
- Do run-level mixed typography:
	- Chinese runs -> Chinese body font style.
	- English words and numbers -> Times New Roman run style.
	- Do not use one rStyle from start to end.

Image strategy:
- Put images in document.images.
- No visible placeholder text is required.
- If paraIndex is uncertain, omit paraIndex and let backend auto-anchor.

Output process:
Step A: build style map for this batch.
Step B: draft paragraphs with explicit run splitting.
Step C: validate style references.
Step D: call generate_document.
```