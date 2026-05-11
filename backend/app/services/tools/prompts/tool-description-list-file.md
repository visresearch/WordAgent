List files and directories under `wence_data/project` (project sandbox only).

## Parameters
- `path` (string, optional): Relative path under `wence_data/project`. Default `"."`.
- `recursive` (bool, optional): Whether to recursively list subdirectories. Default `false`.
- `include_hidden` (bool, optional): Whether to include dotfiles/directories. Default `false`.

## When to use
- You need to discover available files before reading/editing.
- You need to inspect folder structure and candidate target files.

## When not to use
- You already know the exact file path and can directly call `read_file`/`edit_file`.

## Returns
- Text list with one item per line:
  - `[DIR] relative/path/`
  - `[FILE] relative/path.ext (size bytes)`

## Security boundary
- Access is strictly limited to `wence_data/project`.
- Any path outside this root is rejected.
