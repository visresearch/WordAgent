Create or edit text files under `wence_data/project`.

## Signature
`edit_file(path: str, content: str, append: bool = false) -> str`

## Behavior
- Creates file if missing.
- Can append or overwrite.
- Intended for text files (including `md`/`txt`).

## Security
- Access is restricted to `wence_data/project`.
