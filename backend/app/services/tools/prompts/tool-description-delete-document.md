Delete a paragraph range from the Word document.

## Parameters
- `paraIDs` (int[]): paragraph IDs to delete. Each ID is an independent target (NOT a continuous range).
- `docId` (int, optional): target document ID; use `0` for the active document.

## Use
- Delete existing content, or prepare a replacement rewrite before `generate_document`.
- Add-only or analysis-only tasks: do not call this tool.

## Critical notes
- Non-blocking: frontend marks/highlights the range; do not wait for confirmation.
- Continue the planned workflow after calling this tool, including `generate_document` when needed.
- Use paraIDs returned by `search_documnet`/`read_document`. Avoid relying on stale paragraph indices.
- Deletion is pending until user confirms in Word UI. If content still appears immediately after tool call, do NOT retry the same delete again.