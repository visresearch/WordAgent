Search Word document content by text and/or style criteria.

## Parameters
- `query` (object): `DocumentQuery` with `type` (`run` or `paragraph`) and `filters`.
- `docId` (string, optional): target document ID; omit for the active document.

## Use
- Locate paragraphs by keywords, section names, regex, or style clues.
- After matches, call `read_document` around the candidate indices before editing/deleting.
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