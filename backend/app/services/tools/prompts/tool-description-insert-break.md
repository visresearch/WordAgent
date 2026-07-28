Insert a native break immediately after a verified paragraph.

## Parameters

- `paraID`: real paragraph ID from document context, `read_document`, `search_document`, or a previous tool result.
- `breakType`: exactly one of:
  - `wdLineBreak`: Shift+Enter within the current flow.
  - `wdPageBreak`: next page with unchanged page/section settings.
  - `wdSectionBreakNextPage`: next-page section that may change headers, footers, numbering, margins, paper, columns, or orientation.

Use page/section breaks for true pagination; never substitute blank paragraphs or `\n`. Covers are first-page content; abstracts, tables of contents, references, appendices, and top-level chapters normally start on fresh pages unless a user/template specifies otherwise.

Success returns `paragraphAfterBreak` (`paraID`, zero-based `paraIndex`, `pageStart`, `pageEnd`) and `newPage`. Use `paragraphAfterBreak.paraID` as the next generation anchor. WPS returns physical pages; Microsoft Word may return `null` page fields.

On timeout/unknown result, do not repeat the break; read to recover its location.
