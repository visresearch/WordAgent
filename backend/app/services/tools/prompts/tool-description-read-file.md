Read file content from the project sandbox.

## Parameters
- `path` (string): Relative path in the project sandbox.
  - Supports inline line range syntax: `path/to/file:24-25`
- `start_line` (int, optional): 1-based start line.
- `end_line` (int, optional): 1-based end line.

## Capabilities
- Text files: return line-numbered content.
- Image files (`png/jpg/jpeg/webp/bmp/gif/tiff`): return image size attributes and OCR text.
- `pdf`: extract text from pages.
- `docx`: extract paragraph/table text.

## When to use
- Need exact source lines for analysis or patch planning.
- Need to read `md/txt/py/json` style files in the project data area.
- Need text from an image inside project data.

## Returns
- Text content with line numbers for text files.
- OCR text for image files.

## Security boundary
- Access is strictly limited to the project sandbox.
- Any path outside the project root is rejected.
