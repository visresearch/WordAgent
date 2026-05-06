Read paragraph-range content from a Word document through the frontend bridge.

## Parameters:
- `startParaIndex` (int): 0-based inclusive start paragraph index. Default: `0`.
- `endParaIndex` (int): 0-based inclusive end paragraph index. Default: `49`. `-1` means end of document.
- `docId` (string, optional): Document ID to read from. If None, reads from the currently active document. The documentId for each open document is included in the documentMeta sent with each chat message.

## When to use:
- Need original paragraph text/style before rewriting, polishing, or translating.
- Need to inspect context around search hits before deciding edits.

## When not to use:
- User only asks conceptual questions unrelated to current document content.
- You already have enough context from recent reads and no new range is needed.

## Returns:
- `str`: document JSON string for the requested range.
- Empty string on timeout/failure/stop.

## Examples (scenarios):
- User says: “请改写第 30-36 段语气更正式” -> call `read_document` for that range first.
- `search_documnet` returns multiple candidates -> call `read_document` around matched indices to confirm target paragraphs.