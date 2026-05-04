Generate formatted document content for Word.

## Parameters
- `document` (object): DocumentOutput with paragraphs, tables, styles, insertParaIndex

## Critical Format Rules

**document parameter must be a raw JSON object, NOT a JSON string!**
- ✅ `{"document": {"insertParaIndex": -1, "paragraphs": [...], "styles": {...}}}`
- ❌ `{"document": "{\"insertParaIndex\": -1, ...}"}` (escaped string!)
- ❌ `generate_document(document="...")` (string argument!)

## Long Document Strategy
Split documents with 10+ paragraphs into multiple calls (6-12 paragraphs per batch).

## Style Rules
- All style array values MUST be primitives (str, int, float, bool)
- NO `null`, NO `None` in style arrays
- See `system-prompt-default-recommend-document-style.md` for default styles

## Image Rules
- Images are inline runs without `text` field
- Text run: `{"text": "...", "rStyle": "rS_2"}`
- Image run: `{"url": "...", "width": 320, "height": 240, "altText": "..."}`
- Add caption below figures: `图X 描述` with `pS_6` + `rS_5`

## Typography
- Chinese text → `rS_2` (宋体)
- English/numbers in body → `rS_4` (Times New Roman)
- Split mixed content into separate runs

## Table Rules

### Cell Structure
Each table cell MUST have `cStyle` field. Two modes:

**Simple mode (preferred):**
```json
{"text": "内容", "cStyle": "cS_1", "rStyle": "rS_2"}
```

**Multi-paragraph mode:**
```json
{"paragraphs": [{"runs": [{"text": "内容", "rStyle": "rS_2"}], "pStyle": "pS_3"}], "cStyle": "cS_1"}
```

### Table Style Example
```json
{
  "rows": 3,
  "columns": 2,
  "tStyle": "tS_1",
  "cells": [
    [{"text": "Header1", "cStyle": "cS_2", "rStyle": "rS_2"}, {"text": "Header2", "cStyle": "cS_2", "rStyle": "rS_2"}],
    [{"text": "Data1", "cStyle": "cS_1", "rStyle": "rS_2"}, {"text": "Data2", "cStyle": "cS_1", "rStyle": "rS_2"}],
    [{"text": "Data3", "cStyle": "cS_1", "rStyle": "rS_2"}, {"text": "Data4", "cStyle": "cS_1", "rStyle": "rS_2"}]
  ]
}
```

### Required Fields
- `tStyle`: Table style reference (e.g., "tS_1")
- `cStyle`: Cell style reference (e.g., "cS_1") - REQUIRED for every cell
- `rStyle`: Run style reference (e.g., "rS_2") - for text styling

### Cell Style Definitions
Define cell styles in `styles` dict:
```json
"cS_1": ["center", 0, 0, 0, 0, 0, 0, "Table Cell", 0],
"cS_2": ["center", 0, 0, 0, 0, 0, 0, "Header Cell", 1]
```

## Example
```json
{
  "document": {
    "insertParaIndex": -1,
    "paragraphs": [
      {"pStyle": "pS_1", "runs": [{"text": "标题", "rStyle": "rS_1"}]},
      {"pStyle": "pS_3", "runs": [{"text": "正文内容。", "rStyle": "rS_2"}]}
    ],
    "tables": [],
    "styles": {
      "pS_1": ["center", 0, 0, 0, 0, 12, 6, "标题", 1],
      "rS_1": ["黑体", 16, true, false, 0, "#000000", "#000000", 0, false, false, false]
    }
  }
}
```
