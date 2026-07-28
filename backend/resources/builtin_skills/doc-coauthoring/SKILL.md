---
name: doc-coauthoring
description: Guide users through collaborative drafting and revision of substantial Word documents, including proposals, specifications, decision records, PRDs, reports, and structured documentation. Use when the user wants to create, restructure, or iteratively improve a document in WordAgent.
---

# Word Document Co-Authoring

Use three lightweight stages: gather context, draft and refine, then test from a reader's perspective. Do not force the full process for a small edit.

## 1. Gather context

Use conversation history first. Ask only for missing details that change the result: document type, outcome, audience, template, length, tone, deadline, facts, constraints, decisions, alternatives, and unresolved questions.

For an existing Word document, call `read_document` before proposing structural or content changes. Use `search_document` for targeted retrieval in a long document. Read uploaded source files with `read_file`. Use an MCP source only when it is actually available and relevant; otherwise ask the user to provide the needed facts. Never invent organizational facts, decisions, metrics, or citations.

When enough context is present, summarize the intended document and open questions. Do not repeat answered questions.

## 2. Draft and refine in Word

Agree on a short outline before a substantial draft. Start with the core decision or most uncertain section; write summaries last.

Use the active Word document as the primary deliverable:

- Use `insertParaID=0` to insert at the document start, including in a non-empty document.
- For any other position, use real paragraph IDs returned by `read_document` or `search_document`.
- Insert long drafts in ordered batches.
- Preserve existing styles unless the user requests a redesign.
- For a replacement, read the target, call `delete_document` once for its paragraph IDs, verify the returned deletion result, then insert the replacement with `generate_document` using the returned `replacementInsertParaID`. If only some IDs were deleted, re-read and retry only the remaining IDs.
- Change only requested sections.

For each section, clarify the claim, evidence, implications, and action. Present meaningful alternatives when choices remain. Incorporate free-form feedback directly.

## 3. Reader test

After the draft is coherent, review it as a reader who has only the document. For high-stakes or long documents, use `run_sub_agent` with `agent_type="reviewer"` to identify:

- the document's purpose and requested action
- assumptions or terms that are not explained
- unsupported claims or internal contradictions
- missing risks, edge cases, ownership, or next steps
- sections that are repetitive, ambiguous, or too dense

Apply clear fixes through the same paragraph-ID workflow. Ask only about issues requiring new facts or a decision. State what changed and any unresolved items.

## Quality bar

Keep headings informative, paragraphs focused, terminology consistent, and evidence close to the claim it supports. Prefer concrete language over filler. The final document must stand on its own for its intended audience.
