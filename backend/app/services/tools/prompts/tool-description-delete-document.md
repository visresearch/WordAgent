Delete a paragraph range from the Word document.

## Parameters
- `startParaIndex` (int): 0-based inclusive start index.
- `endParaIndex` (int): 0-based inclusive end index; `-1` means end of document.
- `docId` (string, optional): target document ID; omit for the active document.

## Use
- Delete existing content, or prepare a replacement rewrite before `generate_document`.
- Add-only or analysis-only tasks: do not call this tool.

## Critical notes
- Non-blocking: frontend marks/highlights the range; do not wait for confirmation.
- Continue the planned workflow after calling this tool, including `generate_document` when needed.
- Indices must match the current document. If any earlier `generate_document` inserted before the target range, indices shifted upward; call `read_document` or `search_documnet` first to verify the exact paragraphs before deleting.