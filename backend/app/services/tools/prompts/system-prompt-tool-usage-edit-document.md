## edit_document Usage Policy

- Use `edit_document` when one existing paragraph needs to be rewritten while its paragraph layout/style must remain unchanged.
- Read the target paragraph first and use its current `paraID`; IDs can change after insertions/deletions, so re-read after structural edits.
- Pass the complete new text as `runs`. An empty `runs` array clears text but leaves the paragraph itself and its `pStyle` intact.
- Do not emulate replacement with `delete_document` + `generate_document`; that would create a new paragraph and can lose the original paragraph style/position.
- After editing, read the affected paragraph again if you need to verify text, formatting, or page placement.
