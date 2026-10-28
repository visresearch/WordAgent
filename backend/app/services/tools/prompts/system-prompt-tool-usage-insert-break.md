## insert_break Usage Policy

- Use native breaks for pagination, never repeated blank paragraphs, newlines, or spaces.
- Abstracts, contents, references, appendices, and top-level chapters normally start on fresh pages. Follow user/template boundaries; do not add a leading break before the first cover or duplicate existing breaks.
- Fresh-page sequence: finish the preceding block, pass its `lastParagraph.paraID` to `insert_break`, then generate the next block at `paragraphAfterBreak.paraID`. Choose a section break only when independent section settings are needed.
