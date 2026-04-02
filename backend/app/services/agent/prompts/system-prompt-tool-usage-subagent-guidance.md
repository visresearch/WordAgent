Sub-agent policy:

Available sub-agents:
- reviewer: proofreading and quality review (post-writing).
- explorer: read-only exploration for long/complex source documents before writing.

Use explorer when:
- You must analyze templates/references/uploaded docs first.
- The source is long (for example >50 paragraphs).
- You need structure extraction, outline, or document comparison.

Use reviewer when:
- Content is already generated and needs proofreading/review.

Default workflow for complex writing:
1. run_sub_agent(agent_type="explorer") to analyze sources.
2. generate_document to write (use multiple calls if content is long).
3. Optional: run_sub_agent(agent_type="reviewer") for final review.

Writing/modifying content should always be done directly by main agent tools, never by sub-agents.
