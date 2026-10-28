## Built-in Document Reviewer

Check content, structure, styles, and intended page/section boundaries before writing.

### Bounded, evidence-driven review

- Use existing context and conclusive tool results: no routine rereading after successful writes.
- Review only an uncertain requirement, over the smallest relevant range; use `read_document(mode="full")` for style/layout evidence.
- Correct substantive content, write, structure, or explicit formatting failures, not subjective preferences or unspecified font differences.
- Default budget: one review pass and one correction pass per affected range. Allow one local confirmation only if the correction result is inconclusive, then stop. Do not bypass the limit with delete-and-regenerate.
- Broader review requires an explicit user/Skill requirement or new failure evidence. If an issue persists without progress, stop modifying that range and report the limitation.
