## Project Directory Guide (`wence_data/project`)

All file tools (`list_file`, `read_file`, `edit_file`) are sandboxed to `wence_data/project`.

### Common subfolders
- `uploads/`: User uploaded source files (docx/pdf/txt/md/images).
- `temp/`: Temporary runtime artifacts (downloaded images, OCR/intermediate files, cache-like data).
- `skills/`: Local skill packages and `SKILL.md` resources.

### Practical rules
- Use relative paths from `wence_data/project` (for example `uploads/a.md`).
- Never assume a file exists; verify with `list_file` first when uncertain.
- Do not reference or attempt paths outside this root.
