Delete a paragraph range from the Word document.

## Parameters
- `paraIDs` (int[]): paragraph IDs to delete. Each ID is an independent target (NOT a continuous range).
- `docId` (int, optional): target document ID; use `0` for the active document.

## Use
- Delete existing content, or prepare a replacement rewrite before `generate_document`.
- Add-only or analysis-only tasks: do not call this tool.

## Critical notes
- The tool waits for the frontend to execute the deletion immediately under native Track Changes and returns the actual `deletedCount`.
- User confirmation is not required before the Agent continues. The UI confirmation action only accepts or rejects revisions that already exist.
- Continue the planned workflow only after checking the returned `success`, `deletedCount`, `missingParaIDs`, and `failedParaIDs`.
- For a replacement, use the returned `replacementInsertParaID` as the next `generate_document.insertParaID`. A deleted paragraph remains in the native revision object model until acceptance, so reusing its paraID can place new text inside the deletion and make it disappear when revisions are accepted.
- Use paraIDs returned by `search_document`/`read_document`. Avoid relying on stale paragraph indices.
- On partial failure, re-read the document and retry only IDs that still exist. Never blindly repeat the full delete request.
