## read_file Usage Policy

- Read only required files or line ranges; avoid loading large files blindly.
- Prefer line-range reads for targeted debugging (e.g. `path:24-25`).
- For images in project data, use `read_file` to OCR text before reasoning.
- If a file is not found, call `list_file` to verify the path instead of guessing.
