## run_sub_agent Usage Policy

- Use `run_sub_agent(agent_type="explorer")` for long or complex source analysis before writing.
- Use `run_sub_agent(agent_type="reviewer")` only after draft content exists and quality review is needed.
- Keep writing/modification actions in main-agent document tools, not sub-agents.
- For complex tasks (multi-section writing, multi-file synthesis, comparison, long reports), prefer using `explorer` first when additional analysis is needed.
- If document is empty or nearly empty (for example totalParas <= 1 and no explicit source ranges/files), do not call `explorer`; continue with main-agent planning/writing directly.

Recommended complex workflow:
1. Explorer for analysis.
2. Main agent writes via document tools.
3. Optional reviewer for final checks.
