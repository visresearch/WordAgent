## read_document Usage Policy

- Read only the paragraph ranges needed for the current task.
- For broad coverage, read in chunks of at most 50 paragraphs.
- Avoid full-document one-shot reads.
- Prefer targeted follow-up reads around matched paragraph indices.
- For broad reading/understanding/summarization, use `mode="lightweight"` to read paragraph text and paragraph IDs without style details.
- For close reading before editing, formatting-sensitive rewrites, or style/layout inspection, use `mode="full"` to read the complete representation including styles, tables, images, and character formatting.
