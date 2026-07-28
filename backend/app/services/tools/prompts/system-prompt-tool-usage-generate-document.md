## generate_document Usage Policy

- Use for content creation/insertion; do not use for delete-only or analysis-only tasks.
- Generate only new or changed content; never reproduce unchanged document regions.
- Follow the tool schema exactly: one raw object, one ordered `paragraphs` stream, complete referenced styles, a defined non-empty `pStyle` on every paragraph, and a required `insertParaID`.
- Preserve a user/template/Skill format exactly. Use the shared default style only when no format is prescribed.
- Use `insertParaID: 0` only for the document start. Otherwise use a verified nonzero paraID; never invent one.
- For replacement, wait for `delete_document` success and use its `replacementInsertParaID`.
- Split output only for payload size, independent validation, or page/section boundaries. Preserve deterministic order and never separate a table from its neighboring content.
- After success, use `lastParagraph.paraID` as the next append anchor. Its returned index/page fields are authoritative; do not re-read merely to rediscover it.
- Images must be inline runs with a single `url`; keep URLs unchanged and preserve aspect ratio.
- On a timeout/unknown result, do not repeat generation because content may already exist. Re-read the affected location to recover state.
