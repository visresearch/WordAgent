Read a document range using the shared Document Addressing rules.

- Required: `docId`. Range: `startParaIndex` / `endParaIndex` or `startParaID` / `endParaID`.
- `mode="lightweight"`: text, paragraph indices and IDs, plus WPS native formulas as LaTeX.
- `mode="full"` (default): also styles, tables, images, and native page ranges when available.
- Both modes include `meta.pageMarginsCm` when available, with `top`, `bottom`, `left`, and `right` in centimeters. A `null` side means sections have different values for that side. Use `adjust_document` to set page margins.
- Returns an ordered `paragraphs` stream with inline `{ "tables": [...] }` blocks, not a separate top-level `tables` field. Preserve this order when copying content.
- WPS native equations are returned in order as `{"formula":"..."}` runs. A `formulaError` run marks an equation whose LaTeX could not be recovered. Use full mode for table structure around equations.

Table metadata: `rowHeights` is a flat list of heights in points from top to bottom; `rowHeightRules` is a parallel optional list (0=auto, 1=at least, 2=exact; defaults to at least for supplied heights). Read tables also include `paraID` / `endParaID` anchors and native `pageStart` / `pageEnd` when available.
