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
- For each image, provide a placeholder paragraph in `document.paragraphs` with run text `[图片]` (or `/`).
- Keep image `paraIndex` aligned with placeholder paragraph `paraIndex`.
- If unsure, you can omit `paraIndex`; backend will auto-append placeholder paragraphs and anchor images.

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
		"paragraphs": [
			{
				"paraIndex": 0,
				"pStyle": "pS_3",
				"runs": [{ "text": "[图片]", "rStyle": "rS_2" }]
			}
		],
		"tables": [],
		"images": [
			{
				"type": "inline",
				"paraIndex": 0,
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