---
name: internal-comms
description: Draft and revise internal communications in WordAgent, including 3P updates, company newsletters, FAQs, leadership notes, project updates, incident communications, and general announcements. Use whenever the user asks for employee-facing or leadership-facing communication.
---

# Internal Communications

Produce concise, factual communication for the intended internal audience. Use the active Word document as the primary deliverable.

## Select the format

Follow the matching guide included with this skill:

- `examples/3p-updates.md` for Progress, Plans, and Problems updates
- `examples/company-newsletter.md` for company-wide digests
- `examples/faq-answers.md` for employee FAQs
- `examples/general-comms.md` for leadership notes, project updates, incidents, policy notices, and other announcements

## Gather facts

Use information already supplied in the conversation first. For an existing draft or source material in Word, call `read_document`; use `search_document` for targeted retrieval. Read uploaded files with `read_file`.

External systems such as email, chat, calendars, drives, or knowledge bases may be used only when a corresponding MCP tool is available. Do not claim access to a source that is unavailable. Do not fabricate metrics, dates, owners, links, decisions, or quotes. Mark genuinely uncertain information clearly or ask a focused question when it blocks an accurate draft.

Confirm only material gaps such as audience, purpose, time period, desired action, owner, deadline, or approval status. For incident communication, distinguish confirmed facts from investigation status and avoid assigning blame.

## Write in Word

Match the user's language and established company voice. Put the key message and required action first, then supporting context. Use scannable headings and short paragraphs or bullets.

- Document start: use `generate_document(..., insertParaID=0)`, including in an existing document.
- Other positions: read the document and use real paragraph IDs.
- Replacement: call `delete_document` once for the old paragraph IDs, then `generate_document` for the replacement. Do not repeat a pending deletion.
- Preserve existing formatting unless restyling is requested.
- Change only the requested content.

Before finishing, verify names, dates, figures, links, audience, action, owner, and deadline. Remove repetition and unsupported claims.
