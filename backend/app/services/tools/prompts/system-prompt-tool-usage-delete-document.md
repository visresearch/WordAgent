## delete_document Usage Policy

- Use only for explicit delete requests or replacement rewrites.
- For replacements, call `delete_document` before `generate_document`.
- Before deleting, verify uncertain ranges with `read_document` or `search_document`.
- If prior `generate_document` inserted above the target, re-read/search because indices shifted.
- `delete_document` waits for the frontend to execute the deletion immediately under native Track Changes. User confirmation is not required before continuing.
- Check `success`, `deletedCount`, `missingParaIDs`, and `failedParaIDs` before generating replacement content.
- For replacement content, always use the returned `replacementInsertParaID` as `generate_document.insertParaID`; never reuse a paraID that was just deleted, even though native Track Changes may keep it visible until acceptance.
- If the result is partial or failed, re-read the affected range and retry only paragraph IDs that still exist; never blindly repeat the full request.
