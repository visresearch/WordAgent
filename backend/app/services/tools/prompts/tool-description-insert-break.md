Insert a native break immediately after `paraID` in the active document.

`breakType` is one of:
- `wdLineBreak`: Shift+Enter.
- `wdPageBreak`: next page, unchanged section settings.
- `wdSectionBreakNextPage`: next-page section for independent headers, footers, numbering, margins, columns, paper, or orientation.

Success returns `paragraphAfterBreak` with its ID, index, and native page fields when available.
