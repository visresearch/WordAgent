## generate_document Usage Policy

- Generate only new or changed content; do not reproduce unchanged regions or call for delete-only/analysis-only tasks.
- Split output only for payload size, independent validation, or page/section boundaries. Preserve order and keep tables with their neighboring content.

Table metadata: `rowHeights` is a flat list of heights in points from top to bottom; `rowHeightRules` is a parallel optional list (0=auto, 1=at least, 2=exact; defaults to at least for supplied heights). Read tables also include `paraID` / `endParaID` anchors and native `pageStart` / `pageEnd` when available.
