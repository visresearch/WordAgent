Insert a document break immediately after the paragraph identified by `paraID`.

## Parameters
- `paraID` (int): the existing paragraph ID returned by `read_document` or `search_document`.
- `breakType` (string): exactly one of `wdLineBreak`, `wdPageBreak`, or `wdSectionBreakNextPage`.

## Break types
- `wdLineBreak`: line break, equivalent to Shift+Enter.
- `wdPageBreak`: page break; continue on the next page without changing page settings.
- `wdSectionBreakNextPage`: next-page section break; the new section can have different headers, footers, page numbers, or paper orientation.

## Use
- Use the real `paraID` from the document. Do not use a paragraph index or invent an ID.
- Use `wdLineBreak` within a paragraph, `wdPageBreak` for a new page, and `wdSectionBreakNextPage` when the following content needs independent section settings.
- The operation is applied to the active Word/WPS document and returns after the frontend reports execution success or failure.

## Return value
- On success, `paragraphAfterBreak` contains the actual paragraph after the inserted break: `paraID`, zero-based `paraIndex`, `pageStart`, and `pageEnd`.
- `newPage` is the returned `pageStart`. Use `paragraphAfterBreak.paraID` as the anchor for content that must continue after the break.
- WPS returns physical page numbers after repagination. Microsoft Word returns page fields as `null` when unavailable.
- If the return contains a timeout warning, do not repeat the break. Use `read_document` to recover its location.
