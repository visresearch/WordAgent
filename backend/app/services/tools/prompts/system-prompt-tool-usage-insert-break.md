## insert_break Usage Policy

- Call `insert_break` only after identifying the target paragraph with `read_document` or `search_document`.
- The tool accepts exactly two arguments: `paraID` and `breakType`.
- `breakType` must be exactly `wdLineBreak`, `wdPageBreak`, or `wdSectionBreakNextPage`.
- Use `wdLineBreak` for Shift+Enter, `wdPageBreak` for a page break that keeps page settings, and `wdSectionBreakNextPage` for a new section beginning on the next page.
- The operation targets the active document and is non-blocking; do not wait for a separate confirmation before continuing.
