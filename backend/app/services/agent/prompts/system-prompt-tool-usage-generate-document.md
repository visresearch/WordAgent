## generate_document - Hard Constraints

CRITICAL:
- `document` MUST be an object, never a JSON string.
- `document.styles` is REQUIRED.
- Every referenced style ID (`pStyle`/`rStyle`/`cStyle`/`tStyle`) MUST exist in `document.styles`.
- Style definitions in `document.styles` MUST be arrays, not objects.

### Strict call shape
- Correct: `generate_document({"document": {...}})`
- Wrong: `{"document": "{...json string...}"}`

### Style constraints
- Do not use undefined IDs like `title`, `subtitle`, `normal`, `titleFont` unless they are explicitly defined in `styles`.
- Prefer consistent IDs such as `pS_1/pS_2/pS_3/pS_4/pS_5` and `rS_1/rS_2/rS_3`.
- If editing existing content, preserve source `pStyle/rStyle` unless user explicitly asks for format changes.

### Modification rules
- Output only changed/new paragraphs, never unchanged full-document content.
- For existing-content rewrite/polish/translate: call `delete_document` first, then `generate_document` at same index.
- For add-only: call `generate_document` only.

### Long content strategy
- If the content is long (e.g. > 30 paragraphs), split it into multiple `generate_document` calls.
- Each call should use the correct `insertParaIndex` so sections are inserted in order.
- Reuse the same `styles` block across calls — define it in every call.

### Preflight checklist before calling
1. Is `document` an object (not string)?
2. Is `styles` present?
3. Are all style entries arrays?
4. Do all referenced style IDs exist in `styles`?
5. Does `insertParaIndex` match the intended insertion point?

### Minimal safe style template (when creating new content)
Use a complete style set and reference only these IDs:
- `pS_1` main title, `pS_2` section title, `pS_3` body, `pS_4` subsection, `pS_5` table body
- `rS_1` title font, `rS_2` body font, `rS_3` English/number in titles

For new content without explicit user formatting request, prefer this exact canonical style block:
```json
{
	"pS_1": ["center", 0, 0, 0, 0, 12, 6, "标题", 1],
	"pS_2": ["left", 0, 0, 0, 0, 12, 6, "标题 1", 1],
	"pS_4": ["left", 0, 0, 0, 0, 6, 3, "标题 2", 1],
	"pS_3": ["justify", 0, 0, 0, 24, 0, 0, "正文", 1],
	"pS_5": ["center", 0, 0, 0, 0, 0, 0, "正文", 1],
	"rS_1": ["黑体", 16, true, false, 0, "#000000", "#000000", 0, false, false, false],
	"rS_2": ["宋体", 12, false, false, 0, "#000000", "#000000", 0, false, false, false],
	"rS_3": ["Times New Roman", 16, true, false, 0, "#000000", "#000000", 0, false, false, false]
}
```

### Bad vs Good examples

Bad (do NOT do this):
- `document` as string:
```json
{"document": "{\"paragraphs\": [...]}"}
```
- style values as objects/list-of-objects:
```json
"styles": {
	"pS_1": {"name": "标题"},
	"rS_1": [{"fontSize": 12}]
}
```

Good (required shape):
```json
{
	"document": {
		"insertParaIndex": 0,
		"paragraphs": [
			{"pStyle": "pS_1", "runs": [{"text": "Title", "rStyle": "rS_1"}]},
			{"pStyle": "pS_3", "runs": [{"text": "Body text", "rStyle": "rS_2"}]}
		],
		"tables": [],
		"styles": {
			"pS_1": ["center", 18, 0, 0, 0, 12, 6, "标题", 1],
			"pS_3": ["justify", 18, 0, 0, 24, 0, 0, "正文", 1],
			"rS_1": ["黑体", 16, true, false, 0, "#000000", "#000000", 0, false, false, false],
			"rS_2": ["宋体", 12, false, false, 0, "#000000", "#000000", 0, false, false, false]
		}
	}
}
```
