Read a paragraph range from the Word document.

## Parameters
- `startParaIndex` (int, optional): 0-based inclusive start index (index mode).
- `endParaIndex` (int, optional): 0-based inclusive end index; `-1` means end of document (index mode).
- `startParaID` (int, optional): start paragraph ID (paraID mode).
- `endParaID` (int, optional): end paragraph ID (paraID mode). If omitted, equals `startParaID`.
- `docId` (int, optional): target document ID; use `0` for the active document.
- `mode` (string, optional): `"lightweight"` or `"full"`; default `"full"`.

## Use
- Read before rewriting, polishing, translating, deleting, or verifying search results.
- Read only needed ranges; chunk broad reads into <= 50 paragraphs.
- Skip if recent context already covers the needed range.
- Provide either paraIndex range OR paraID range (prefer paraID when IDs are known).
- Use `mode="lightweight"` for broad reading, outline/summary discovery, and understanding article text. It returns paragraph text plus paragraph indices/IDs, but no style, table, image, or character formatting detail.
- Use `mode="full"` when you need precise style/layout information, tables/images, or when preparing to edit/rewrite content while preserving formatting.
