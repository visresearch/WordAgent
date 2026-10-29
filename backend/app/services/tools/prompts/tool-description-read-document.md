Read a document range using the shared Document Addressing rules.

- Required: `docId`. Range: `startParaIndex` / `endParaIndex` or `startParaID` / `endParaID`.
- `mode="lightweight"`: text, paragraph indices, and IDs only.
- `mode="full"` (default): also styles, tables, images, and native page ranges when available.
- Returns an ordered `paragraphs` stream with inline `{ "tables": [...] }` blocks, not a separate top-level `tables` field. Preserve this order when copying content.

Table metadata: `rowHeights` is a flat list of heights in points from top to bottom; `rowHeightRules` is a parallel optional list (0=auto, 1=at least, 2=exact; defaults to at least for supplied heights). Read tables also include `paraID` / `endParaID` anchors and native `pageStart` / `pageEnd` when available.
