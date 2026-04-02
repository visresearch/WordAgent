Tool strategy:
- Search first, then read
- Do not read full document in one call
- Use chunked reads (<= 50 paragraphs each)
- For modify/rewrite/translate existing content: delete_document + generate_document
- For add-only: generate_document only
- For delete-only: delete_document only
- Before each generate_document call, run preflight: document must be object, styles required, all referenced style IDs must exist, style values must be arrays
