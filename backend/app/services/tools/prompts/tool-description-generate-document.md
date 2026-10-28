Insert formatted content using a raw `document: DocumentOutput` object, required `insertParaID`, and optional `docId` (default `0`).

- Pass `document` as an object, not an escaped JSON string or an extra nested wrapper.
- `document.paragraphs` is the ordered paragraph/table-block stream; no top-level `document.tables` or synthetic placement indices.
- Text runs require `rStyle`. Define every referenced style in `document.styles`; paragraph/run/cell/table arrays require at least 9/11/4/1 primitive values respectively, with no `null`.
- Images are inline URL runs, with no `text`; keep URLs unchanged and preserve aspect ratio.
- Success returns `lastParagraph` with its ID, index, and native page range when available. Use `lastParagraph.paraID` for the next append.
