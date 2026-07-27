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
- The operation is applied to the active Word/WPS document and is non-blocking. Continue the workflow after calling it.
