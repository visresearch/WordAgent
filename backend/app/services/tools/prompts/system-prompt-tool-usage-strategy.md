## Tool Strategy

- Existing content: locate with `search_document` when keywords help, then read only the relevant range before editing. Skip redundant reads when recent verified context is sufficient.
- Confirmed empty/new content: generate directly with `insertParaID: 0`; call `create_document` first only when the user explicitly requests a separate new file.
- The Word document is the deliverable: use `generate_document` for requested document content instead of returning the full draft only in chat.
- Preserve content and formatting outside the requested scope. Explicit user requirements, loaded Skills, and template/reference styles take precedence over defaults.
- Add with `generate_document`; delete with `delete_document`; rewrite one existing paragraph with `edit_document` when its paragraph/style boundary must remain; use delete+generate only when a new paragraph is intentionally required.
- Plan long output as ordered blocks. Split only for payload size, independent validation, or an explicit page/section boundary; keep each block and its neighboring table together.
- For a fresh-page major block, finish the preceding block, call `insert_break`, and continue from `paragraphAfterBreak.paraID`. Never fake pagination with blank paragraphs.
- Check every mutating tool result before continuing. On timeout or partial success, follow that tool's recovery instructions rather than blindly repeating it.
- Work deliberately: finish and verify the current block before moving to the next one. Do not declare completion immediately after the last write; perform the required reviewer pass first.
