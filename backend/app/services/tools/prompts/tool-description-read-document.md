Read a document range using the shared Document Addressing rules.

- Required: `docId`. Range: `startParaIndex` / `endParaIndex` or `startParaID` / `endParaID`.
- `mode="lightweight"`: text, paragraph indices, and IDs only.
- `mode="full"` (default): also styles, tables, images, and native page ranges when available.
- Returns an ordered `paragraphs` stream with inline `{ "tables": [...] }` blocks, not a separate top-level `tables` field. Preserve this order when copying content.
