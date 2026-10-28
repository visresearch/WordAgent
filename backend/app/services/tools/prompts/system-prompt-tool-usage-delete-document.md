## delete_document Usage Policy

- Use only for requested deletion or replacement requiring new paragraphs; verify uncertain targets first.
- For deleting all content, collect all paragraph IDs from a complete current read, including blank paragraphs and table-cell paragraphs. A local selection or search matches alone do not establish complete coverage.
- Check `success`, `deletedCount`, `missingParaIDs`, and `failedParaIDs` before generating replacement content.
- After successful deletion, use `replacementInsertParaID` for replacement generation. Never reuse a deleted ID: Track Changes may retain it until acceptance, causing inserted text to disappear with the deletion.
