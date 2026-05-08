Read file content from `wence_data/project` safely.

## Signature
`read_file(path: str, start_line: int | None = None, end_line: int | None = None) -> str`

## Capabilities
- Text files: line-numbered content.
- Image files: image size attributes + OCR text extraction.
- `pdf`: extract text from pages.
- `docx`: extract paragraph/table text.

## Notes
- Supports inline line-range syntax in path: `relative/path.py:24-25`.
- Access is restricted to `wence_data/project`.
