## edit_document Usage Policy

### Core Principle
- `edit_document` updates content **while preserving the original paragraph/cell structure and styling** (`pStyle`, formatting, position).
- Always read the target paragraph/cell first to understand its current style, then compose the new content to match that style.


### Paragraph Editing
- Use `edit_document` when one existing paragraph needs to be rewritten while its paragraph layout/style must remain unchanged.
- Read the target paragraph first and use its current `paraID`; IDs can change after insertions/deletions, so re-read after structural edits.
- Pass the complete new text as `runs`. An empty `runs` array clears text but leaves the paragraph itself and its `pStyle` intact.
- Do not emulate replacement with `delete_document` + `generate_document`; that would create a new paragraph and can lose the original paragraph style/position.
- After editing, read the affected paragraph again if you need to verify text, formatting, or page placement.

### Table Cell Editing
- Tables are composed of cells, where each cell is treated as a special paragraph with a `paraID`.
- To edit table cell content, use `edit_document` with the target cell's `paraID`, following the same workflow as paragraph editing.
- Reading the table structure first to obtain the correct `paraID` for each cell; cell `paraID`s may change after row/column operations, so re-read after structural modifications.
- Pass the complete new text as `runs`. An empty `runs` array clears the cell content but preserves the cell structure and formatting.
- Do not delete and regenerate cells to update content; this may disrupt table structure, cell borders, or column widths.
- After editing, verify the cell content and table layout if needed.