List files and directories under `wence_data/project` (project sandbox only).

## Signature
`list_file(path: str = ".", recursive: bool = false, include_hidden: bool = false) -> str`

## Use cases
- Discover available files before reading/editing.
- Inspect folder structure for research data collection.

## Security
- Paths are restricted to `wence_data/project` only.
