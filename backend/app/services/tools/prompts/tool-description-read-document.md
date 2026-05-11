Read a paragraph range from the Word document.

## Parameters
- `startParaIndex` (int): 0-based inclusive start index.
- `endParaIndex` (int): 0-based inclusive end index; `-1` means end of document.
- `docId` (string, optional): target document ID; omit for the active document.

## Use
- Read before rewriting, polishing, translating, deleting, or verifying search results.
- Read only needed ranges; chunk broad reads into <= 50 paragraphs.
- Skip if recent context already covers the needed range.