---
name: theme-factory
description: Apply a consistent professional color and typography theme to Word documents in WordAgent. Use when the user asks to style, restyle, brand, or improve the visual consistency of a report, proposal, brief, manual, or other Word document.
---

# Word Theme Factory

Apply a coherent theme to the active Word document while preserving readability, hierarchy, and content.

## Choose a theme

If the user names a theme, use it directly. Otherwise recommend one or two options based on the document's purpose and audience; do not require the user to open `theme-showcase.pdf`.

Available themes:

- Ocean Depths: calm corporate and financial work
- Sunset Boulevard: energetic marketing and event material
- Forest Canopy: sustainability and wellness content
- Modern Minimalist: neutral reports and technical documents
- Golden Hour: hospitality and editorial material
- Arctic Frost: precise healthcare and technology documents
- Desert Rose: elegant lifestyle and design content
- Tech Innovation: high-contrast technology material
- Botanical Garden: fresh food, agriculture, and nature content
- Midnight Galaxy: dramatic creative and premium content

After selection, use the corresponding `themes/<theme-name>.md` values. For a custom theme, define a small palette with primary, accent, neutral/background, and text colors plus heading and body fonts.

## Apply in WordAgent

Call `read_document` first to inspect the complete document structure, paragraph IDs, and existing styles. Map the theme into `generate_document` styles:

- heading runs: theme header font, bold, dark primary color
- body runs: theme body font, high-contrast text color
- accents: secondary color for short emphasis, labels, or table headers
- backgrounds and highlights: use sparingly; never sacrifice contrast
- tables: consistent header treatment, restrained borders, readable body cells

Use complete WordAgent style arrays and define every referenced style ID. Fonts may not exist on every WPS installation: preserve a suitable existing font or fall back to Arial/Calibri for Latin text and Microsoft YaHei/SimSun for Chinese text. Do not change the document language or wording merely to apply a theme.

For an empty document, the first write uses `insertParaID=0`. For an existing document, use real paragraph IDs. Restyling existing content is a replacement operation: call `delete_document` once for each affected paragraph ID, then insert the same text with themed styles through `generate_document`. Do not repeatedly delete content that is awaiting confirmation in Word.

Work in small ordered batches and preserve paragraph order, tables, links, images, and semantic emphasis. Unless the user requests a full redesign, modify only the selected range.

## Quality checks

Keep body text readable, headings visibly hierarchical, accents restrained, and contrast strong. Use no more than two font families and a small set of repeated styles. Verify that the result remains professional in WPS even when a preferred font falls back.
