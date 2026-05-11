## create_workflow Usage Policy

- MUST call `create_workflow` tool for workflow output. Do NOT output as plain text.
- Keep task descriptions specific and actionable.
- Set `depends_on` correctly to ensure data flows between steps.
- Simpler tasks may not need all agent types.

## Workflow Design Principles
1. **Research first** if web information is needed
2. **Outline before write** for complex documents
3. **Review for quality** on important/long documents
4. **Skip unnecessary steps** for simple tasks

## Common Patterns
- Simple Q&A: No workflow needed
- Document modification: Writer only
- Web research + write: Research -> Writer
- Full pipeline: Research -> Outline -> Writer -> Reviewer
