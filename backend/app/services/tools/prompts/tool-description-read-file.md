Read a project file.

- `path`: relative file path; supports `path:24-25`.
- `start_line` / `end_line`: optional 1-based line range.
- Text returns numbered lines; PDF/DOCX returns extracted text. PDF reading requires the optional PDF plugin; if unavailable, ask the user to install wordagent-plugin-pdf from Settings > Plugins.
- Images return dimensions and OCR text when the OCR plugin is installed, otherwise an availability message.
