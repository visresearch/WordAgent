Read paragraph-range content from the active Word document through the frontend bridge.

## Function Signature
```
read_document(startParaIndex: int, endParaIndex: int) -> str
```

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `startParaIndex` | integer | 0 | 0-based inclusive start index |
| `endParaIndex` | integer | 49 | 0-based inclusive end index, `-1` = end of document |

## When to Use

- **Before writing**: Read original paragraph text/style to maintain consistency
- **Before rewriting**: Understand current content and structure
- **Before translating**: Review original text context
- **Before editing**: Verify search matches and surrounding context
- **For outlines**: Read key sections that define document structure

## When NOT to Use

- Plain conversational responses (just speak)
- Conceptual questions unrelated to document content
- When you already have sufficient context from recent reads

## Returns

JSON string containing paragraph data for the requested range:
```json
{
  "paragraphs": [
    {"index": 0, "text": "...", "style": "..."},
    {"index": 1, "text": "...", "style": "..."}
  ],
  "total": 50
}
```

Returns empty string on timeout, failure, or stop requested.

## Usage Examples

| Task | Call |
|------|------|
| Read first 50 paragraphs | `read_document(0, 49)` |
| Read paragraphs 30-60 | `read_document(30, 60)` |
| Read to end of document | `read_document(100, -1)` |
| Read around search hit | `read_document(45, 55)` |

## Best Practices

1. **Targeted reads**: Read only the range needed, not entire document
2. **Chunked access**: Read max 50 paragraphs per call for efficiency
3. **Verify context**: After search, read around matched indices to confirm
4. **Structure awareness**: Understand document structure before major edits
