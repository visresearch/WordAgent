Read a project file.

- `path`: relative file path; supports `path:24-25`.
- `start_line` / `end_line`: optional 1-based line range.
- Text returns numbered lines; PDF/DOCX returns extracted text.
- Images return dimensions and OCR text when the OCR plugin is installed, otherwise an availability message.
