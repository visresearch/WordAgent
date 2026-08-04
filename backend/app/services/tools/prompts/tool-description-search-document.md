Search Word document content by text and/or style criteria.

## Parameters
- `query` (object): `DocumentQuery` with `type` (`run` or `paragraph`) and `filters`.
- `docId` (int, required): target document ID; use `0` only when the active document is explicitly intended.

## Use
- Locate paragraphs by keywords, section names, regex, or style clues.
- Returned matches include both `paragraphIndex` and `paragraphId`; prefer `paragraphId` for follow-up edit/delete operations.
- After matches, call `read_document` around candidate paraIDs/indices before editing/deleting.
- If the target paragraph range is already certain, skip search.

## Example
```json
{
	"docId": 123,
	"query": {
		"type": "run",
		"filters": { "regex": "风险评估", "regexFlags": "i" }
	}
}
```
