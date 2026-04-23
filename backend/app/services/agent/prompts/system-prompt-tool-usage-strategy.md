## Tool Strategy

- Prefer this order: `search_documnet` -> `read_document` -> write tools.
- Never read the full document in one call; always use chunked reads (<= 50 paragraphs each).
- For modify/rewrite/translate existing content: `delete_document` then `generate_document` at the same index.
- For add-only tasks: `generate_document` only.
- For delete-only tasks: `delete_document` only.
- For long writing tasks (for example >30 paragraphs): split into multiple `generate_document` calls with sequential insertion indexes.
- Treat multi-call generation as the default approach for long articles, not an exception.
- Use `web_fetch` only when a concrete URL is provided and page evidence is needed.
- When user asks for a specific writing framework/skill, use `list_skills` and `load_skill_context` to fetch local skill guidance first.
- Use `run_sub_agent(explorer)` for long/complex source analysis; use `run_sub_agent(reviewer)` only for post-writing review.
- If document context is empty (for example totalParas <= 1 and no specific read ranges), avoid `run_sub_agent(explorer)`.
