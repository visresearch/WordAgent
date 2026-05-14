Search Word document content by text and/or style criteria.

## Parameters
- `query` (object): `DocumentQuery` with `type` (`run` or `paragraph`) and `filters`.
- `docId` (int, optional): target document ID; use `0` for the active document.

## Use
- Locate paragraphs by keywords, section names, regex, or style clues.
- Returned matches include both `paragraphIndex` and `paragraphId`; prefer `paragraphId` for follow-up edit/delete operations.
- After matches, call `read_document` around candidate paraIDs/indices before editing/deleting.
- If the target paragraph range is already certain, skip search.

## Example
```json
{
	"query": {
		"type": "run",
		"filters": { "regex": "风险评估", "regexFlags": "i" }
	}
}
```