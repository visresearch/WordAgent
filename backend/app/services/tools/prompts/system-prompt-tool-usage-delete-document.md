## delete_document Usage Policy

- Use only for explicit delete requests or replacement rewrites.
- For replacements, call `delete_document` before `generate_document`.
- Before deleting, verify uncertain ranges with `read_document` or `search_documnet`.
- If prior `generate_document` inserted above the target, re-read/search because indices shifted.
- Non-blocking: frontend may confirm later; continue the planned workflow.
- IMPORTANT: `delete_document` does not execute immediate hard delete in Word. It marks pending deletions and waits for user confirmation.
- If deleted paragraphs still appear right after calling `delete_document`, DO NOT panic and DO NOT call `delete_document` again for the same paraIDs.
