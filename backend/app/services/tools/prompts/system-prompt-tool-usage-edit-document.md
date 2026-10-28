## edit_document Usage Policy

- Use for rewriting an existing paragraph, including a paragraph inside a table cell, while preserving its structure and position. Use its current content/styles to compose matching runs.
- Changes text and run styles (`rStyle`), not paragraph styles (`pStyle`); do not retry it to change paragraph layout.
- Do not delete and regenerate for this operation: that can lose paragraph formatting or damage table structure.
