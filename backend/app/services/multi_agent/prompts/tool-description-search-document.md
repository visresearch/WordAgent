Search document content by text patterns or style conditions.

## Function Signature
```
search_document(query: SearchQuery) -> str
```

## Parameters

### `query` (required)
Search query object:

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | "run" (text level) or "paragraph" (paragraph level) |
| `filters` | object | Combined with AND semantics |

### Filter Options

| Filter | Type | Description | Example |
|--------|------|-------------|---------|
| `regex` | string | Regular expression pattern | `{"regex": "error|warning"}` |
| `regexFlags` | string | Regex flags | `"i"` for case-insensitive |
| `fontName` | string | Font family | `"SimSun"`, `"Arial"` |
| `fontSize` | number | Font size | `12`, `14` |
| `bold` | boolean | Bold text | `true` |
| `italic` | boolean | Italic text | `true` |
| `underline` | boolean | Underlined text | `true` |
| `color` | string | Text color | `"#FF0000"`, `"#0000FF"` |
| `highlight` | number | Highlight color | `1-7` |
| `alignment` | string | Paragraph alignment | `"center"`, `"left"` |
| `styleName` | string | Word style name | `"Heading 1"`, `"Title"` |

## Common Search Patterns

| Task | Query |
|------|-------|
| Find keyword | `{"type": "run", "filters": {"regex": "keyword"}}` |
| Find case-insensitive | `{"type": "run", "filters": {"regex": "keyword", "regexFlags": "i"}}` |
| Find all headings | `{"type": "paragraph", "filters": {"styleName": "Heading"}}` |
| Find red text | `{"type": "run", "filters": {"color": "#FF0000"}}` |
| Find bold italic | `{"type": "run", "filters": {"bold": true, "italic": true}}` |
| Find centered paragraphs | `{"type": "paragraph", "filters": {"alignment": "center"}}` |
| Find specific section | `{"type": "paragraph", "filters": {"regex": "^第.*章"}}` |

## Returns

```json
{
  "matches": [
    {"text": "matched text", "paragraphIndex": 5, "runIndex": 2},
    {"text": "matched text", "paragraphIndex": 12, "runIndex": 0}
  ],
  "matchCount": 2,
  "matchedParaIndices": [5, 12]
}
```

| Field | Description |
|-------|-------------|
| `matches` | Array of match objects with text and indices |
| `matchCount` | Total number of matches |
| `matchedParaIndices` | Sorted unique paragraph indices |

## Workflow

1. **Search**: Use `search_document` with appropriate filters
2. **Verify**: Use `read_document` around matched indices
3. **Act**: Edit, delete, or rewrite based on findings

## Retry Strategy

If `matchCount: 0`:
1. Try alternative keywords (synonyms, abbreviations)
2. Try partial matches (`"keyword"` → `"key"`)
3. Try different filters (style vs text)
4. Only report "not found" after multiple retries

## Examples

```javascript
// Find all mentions of "AI"
search_document({
  "type": "run",
  "filters": {"regex": "AI|人工智能|机器学习"}
})

// Find document title
search_document({
  "type": "paragraph",
  "filters": {"styleName": "Title"}
})

// Find highlighted text
search_document({
  "type": "run",
  "filters": {"highlight": 6}
})
```
