Delete one continuous, inclusive range from `startParaID` through `endParaID` in `docId` (default `0`). Omit `endParaID` to delete one paragraph. Endpoints are current paragraph IDs in document order, never numerical bounds or indices; `paraIDs` lists are not supported.

Deletes all paragraphs and complete tables in the range. This is the only supported way to delete a table: use its returned `paraID` / `endParaID`, or verified surrounding paragraphs. Partially covered tables, missing endpoints, and reversed ranges are rejected before deletion; boundaries are never expanded automatically.

Waits for frontend execution under native Track Changes. Confirmation accepts/rejects existing revisions. Returns actual paragraph/table deletion counts, failed/missing IDs, and `replacementInsertParaID`. Re-read after a partial or unknown result before retrying.
