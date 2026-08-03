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
- Use `mode="full"` when you need precise style/layout information, tables/images, or when preparing to edit/rewrite content while preserving formatting. Full-mode paragraph objects include `pageStart` and `pageEnd`, the 1-based pages containing the paragraph's first and last positions, when the client exposes native page information. Clients that cannot obtain native page information omit these fields.
- The returned `paragraphs` array is an ordered content stream. Ordinary items are paragraphs; `{ "tables": [...] }` items are table blocks at their exact document positions. Preserve this order when passing cloned content to `generate_document`. There is no parallel top-level `tables` field in the tool result.
