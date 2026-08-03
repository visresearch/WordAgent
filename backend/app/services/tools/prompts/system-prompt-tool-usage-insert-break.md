## insert_break Usage Policy

- Use a verified paragraph ID. `wdLineBreak` is Shift+Enter; `wdPageBreak` starts a new page with unchanged settings; `wdSectionBreakNextPage` starts a new section whose headers, footers, numbering, margins, columns, paper, or orientation may differ.
- Covers, Chinese/English abstracts, tables of contents, references, appendices, and top-level chapters normally start on fresh pages. Do not place a major heading in leftover space at the bottom of the previous page.
- The first cover starts at document position `0` without a leading break. Template/reference breaks take precedence; never add a duplicate break.
- Never simulate pagination with repeated blank paragraphs, newlines, or spaces.
- After success, continue from `paragraphAfterBreak.paraID`; trust its returned index and any present native page fields, and do not re-read only to rediscover the anchor.
- On timeout/unknown result, do not repeat the break. Re-read to recover its location.

### Required fresh-page sequence
1. Generate the complete preceding block, for example the cover.
2. Read `lastParagraph.paraID` from that `generate_document` result.
3. Call `insert_break({"paraID": <lastParagraph.paraID>, "breakType": "wdPageBreak"})`.
4. Read `paragraphAfterBreak.paraID` from the result.
5. Generate the next block, for example the abstract, with `insertParaID` set to that returned ID.

Use `wdSectionBreakNextPage` instead when the next block needs independent section settings.
