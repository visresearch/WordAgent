## Tool Strategy

- Locate before editing: `search_document` when needed, then `read_document`, then write tools.
- Read only needed ranges; chunk broad reads into <= 50 paragraphs.
- Add-only: `generate_document`. Delete-only: `delete_document`.
- If the user explicitly requests a separate new blank document, call `create_document` first, then use `generate_document` with `insertParaID: 0` for the first write.
- Rewrite/polish/translate existing ranges: delete old content, then generate the replacement using the returned `replacementInsertParaID`.
- Long writing: batch `generate_document` calls in stable order.
- Use sub-agents for long source analysis or final review, not for simple/empty-document tasks.
- `delete_document` returns only after the frontend has applied the native tracked deletion. Check its result before continuing; on partial failure, re-read and retry only IDs that still exist.
