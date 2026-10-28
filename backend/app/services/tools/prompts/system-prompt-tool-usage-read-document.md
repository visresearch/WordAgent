## read_document Usage Policy

- Read only missing context; skip reads when recent verified content already covers the task.
- Use `mode="lightweight"` for broad text reading or collecting IDs, including whole-document deletion. Whole-document reads are allowed when the task requires complete coverage.
- Use `mode="full"` for tables, images, or formatting-sensitive edits. For long detailed reads, use chunks of at most 50 paragraphs and cover the entire required range.
