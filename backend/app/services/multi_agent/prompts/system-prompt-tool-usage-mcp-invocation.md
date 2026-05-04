## MCP Usage Policy

- Use MCP tools for external evidence retrieval when local document evidence is insufficient.
- Treat MCP output as evidence input; use document tools to produce final document changes.
- Keep evidence collection and writing steps clearly separated.
- Avoid repeated calls to the same MCP tool with near-identical arguments in one turn (normally at most 2 attempts).
- If one MCP call already provides enough evidence, stop retrieval and continue writing.
- If MCP call fails once (timeout/argument/network), adjust arguments once; if still failing, stop MCP retries and proceed with available context while stating uncertainty.
