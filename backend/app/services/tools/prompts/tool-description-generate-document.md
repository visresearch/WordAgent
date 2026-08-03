Generate formatted content and insert it into the active WPS/Microsoft Word document.

## Parameters

- `document`: raw `DocumentOutput` object, not an escaped JSON string and not another nested `{ "document": ... }` wrapper.
- `insertParaID` (required): `0` inserts at document start; a verified nonzero paraID inserts after that paragraph.
- `docId`: target document ID; `0` means active document.

## Required document shape

- Tool args are one balanced object: `{ "document": {...}, "insertParaID": 123, "docId": 0 }`.
- `document.paragraphs` is the only ordered content stream. Each item is either a paragraph or `{ "tables": [...] }`; never use top-level `document.tables`, synthetic positions, or paraIndex values for placement.
- `document.styles` defines every referenced `pStyle`, `rStyle`, `cStyle`, and `tStyle`.
- Style array lengths: paragraph 9, run 11, cell 4, table 1. Use valid primitives, never `null`/`None`.
- Every paragraph, including an intentional blank with `runs: []`, has a defined non-empty `pStyle`. Text runs have a defined `rStyle`.
- Body English uses `Times New Roman`; split mixed Chinese-English content into separate runs while preserving the required Chinese font.
- Never put `\n` inside `run.text`; use separate paragraphs. Avoid raw ASCII `"` inside text fields; use typographic/Chinese quotation marks.
- Image run: `{ "url": "...", "width": 320, "height": 240, "altText": "..." }` with no `text`. Keep the URL unchanged and preserve aspect ratio.

Example ordered stream:

```json
{
  "document": {
    "paragraphs": [
      {"pStyle":"pS_3","runs":[{"text":"表格前。","rStyle":"rS_2"}]},
      {"tables":[{"rows":1,"columns":1,"cells":[[{"text":"内容","rStyle":"rS_2","cStyle":"cS_1"}]],"tStyle":"tS_1"}]},
      {"pStyle":"pS_3","runs":[]}
    ],
    "styles": {
      "pS_3":["justify",0,0,0,24,0,0,"正文",1],
      "rS_2":["宋体",12,false,false,0,"#000000","#000000",0,false,false,false],
      "cS_1":[1,1,"center","center"],
      "tS_1":[1]
    }
  },
  "insertParaID": 123
}
```

## Anchors and results

- A confirmed empty document's first write uses `insertParaID: 0`; do not read merely to obtain its placeholder paragraph ID.
- Use real paraIDs from document context/read/search. For replacement, use `delete_document.replacementInsertParaID`.
- Success returns `lastParagraph` with `paraID` and zero-based `paraIndex`. When the client native API exposes physical pages, it also includes `pageStart` and `pageEnd`; otherwise those fields are omitted. Use its paraID for the next immediate append.
- On timeout/unknown result, do not repeat generation because content may already exist; read the affected location to recover state.
