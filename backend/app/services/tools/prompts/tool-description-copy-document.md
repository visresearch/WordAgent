Copy an inclusive source paragraph range into an existing target document using the editor's native formatted content.

- `sourceDocID` and `targetDocID` identify the open source and target documents.
- `start_paraID` and `end_paraID` are paragraph IDs from the source, in source order. Use the same ID twice for one paragraph. Include complete tables.
- `insertID` is a paragraph ID from the target. Insert after that paragraph, or pass 0 to insert at the beginning.
- In WPS, pass distinct IDs for cross-document copying. The Word add-in currently exposes only its attached document, so both document IDs must be 0 there.
