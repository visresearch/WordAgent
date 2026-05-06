Search document content by text and/or style criteria (`search_documnet`).

## Parameters:
- `query` (object, DocumentQuery): includes search type (`run`/`paragraph`) and filter conditions.
- `docId` (string, optional): Document ID to search in. If None, searches in the currently active document. The documentId for each open document is included in the documentMeta sent with each chat message.

## When to use:
- User provides concrete keywords, section names, or style clues.
- Need to locate candidate paragraphs before targeted reading or editing.

## When not to use:
- Target paragraph range is already explicitly known.
- Task does not depend on locating existing document content.

## Returns:
- `str` (JSON): includes match details, matched paragraph indices, and suggested follow-up read ranges.

## JSON construction examples:

Minimal keyword search:
```json
{
	"query": {
		"type": "run",
		"filters": {
			"regex": "风险评估",
			"regexFlags": "i"
		}
	}
}
```

Style-oriented paragraph search:
```json
{
	"query": {
		"type": "paragraph",
		"filters": {
			"styleName": "标题 2",
			"alignment": "left"
		}
	}
}
```

## Examples (scenarios):
- User says: “找出所有包含‘风险评估’的段落” -> call `search_documnet`, then read matched ranges.
- User says: “把所有加粗的小标题统一格式” -> call `search_documnet` with style-related filters to locate candidates.