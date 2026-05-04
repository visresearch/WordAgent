Mark document paragraphs for deletion.

## Function Signature
```
delete_document(startParaIndex: int, endParaIndex: int) -> str
```

## Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `startParaIndex` | integer | Start index (0-based, inclusive) |
| `endParaIndex` | integer | End index (0-based, inclusive), `-1` = to end |

## When to Use

- User says: "Delete paragraph X"
- User says: "Remove this section"
- User says: "Delete content from line X to Y"
- After `search_document` locates target content

## Important Behavior

**This is NON-BLOCKING:**
1. Sends deletion request and returns immediately
2. Frontend highlights paragraphs with blue annotations
3. User must confirm on frontend
4. You do NOT wait for user confirmation

## Workflow

```
1. search_document({"type": "run", "filters": {"regex": "target"}})
   → Returns matched indices

2. read_document(start, end)
   → Verify indices are correct

3. delete_document(start, end)
   → Returns immediately, paragraphs highlighted

4. User confirms on frontend
   → Actual deletion happens
```

## Returns

Confirmation string:
```
"已通知前端标记删除段落 5 - 12，等待用户确认"
```

## Important Notes

| Warning | Description |
|---------|-------------|
| Non-blocking | Returns immediately without waiting |
| User confirmation | Required before actual deletion |
| Highlighted | Paragraphs shown in blue on frontend |
| Irreversible | Once confirmed, cannot be undone |

## Common Usage

| Task | Call |
|------|------|
| Delete paragraph 5 | `delete_document(5, 5)` |
| Delete paragraphs 5-12 | `delete_document(5, 12)` |
| Delete to end | `delete_document(5, -1)` |
| Delete from start | `delete_document(0, -1)` |

## Error Handling

- If indices seem wrong: Verify with `read_document` first
- If user cancels: No action taken, just speak naturally
- If document modified: Indices may shift, re-search if needed
