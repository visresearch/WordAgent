## insert_break Usage Policy

- Call `insert_break` only after identifying the target paragraph with `read_document` or `search_document`.
- The tool accepts exactly two arguments: `paraID` and `breakType`.
- `breakType` must be exactly `wdLineBreak`, `wdPageBreak`, or `wdSectionBreakNextPage`.
- Use `wdLineBreak` for Shift+Enter, `wdPageBreak` for a page break that keeps page settings, and `wdSectionBreakNextPage` for a new section beginning on the next page.
- After success, use returned `paragraphAfterBreak.paraID` for content that must continue after the break. Its `paraIndex` and `pageStart/pageEnd` are authoritative frontend locations; do not guess another blank paragraph.
- The tool waits for the frontend execution result. Do not make an extra `read_document` call merely to rediscover the post-break anchor when `paragraphAfterBreak` is present.
