## delete_document Usage Policy

- Call only when the user explicitly asks to delete content, or when preparing a replacement rewrite.
- For replacement workflows, call `delete_document` immediately before `generate_document`.
- Do not call delete tools for add-only requests.
- `delete_document` is non-blocking; do not stop or wait for a per-delete confirm callback.
- Frontend may batch pending deletes and confirm them with one final button after agent execution; continue full tool workflow before finishing.
