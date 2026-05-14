## Tool Strategy

- Locate before editing: `search_documnet` when needed, then `read_document`, then write tools.
- Read only needed ranges; chunk broad reads into <= 50 paragraphs.
- Add-only: `generate_document`. Delete-only: `delete_document`.
- Rewrite/polish/translate existing ranges: delete old content, then generate replacement at the same index.
- Long writing: batch `generate_document` calls in stable order.
- Use sub-agents for long source analysis or final review, not for simple/empty-document tasks.
- `delete_document` is asynchronous/pending-confirmation in frontend. If deleted content still appears immediately, do NOT issue duplicate delete calls for the same paraIDs.
