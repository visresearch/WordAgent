# WordAgent Compatibility Review

Review a skill for execution fit:

- Critical instructions appear within the first 3000 characters of `SKILL.md`.
- Total companion Markdown is concise enough for the 12000-character load budget.
- Tool names exactly match WordAgent tools.
- Word changes use real paragraph IDs and the delete-then-generate replacement flow.
- Instructions do not depend on vendor-specific artifact systems, unavailable connectors, or shell access.
- Facts, paths, input limits, error handling, and user-visible outputs are explicit.

Report concrete issues and the smallest effective correction.
