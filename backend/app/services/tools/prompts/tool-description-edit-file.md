Create or edit text files under `wence_data/project` (safe sandbox).

## Parameters
- `path` (string): Relative file path under `wence_data/project`.
- `content` (string): Content to write.
- `append` (bool, optional): If true, append content; otherwise overwrite. Default `false`.

## Behavior
- If target file does not exist, it is created automatically.
- Parent directories are created automatically when needed.
- Supports text-oriented file types (including `md` and `txt`).

## When to use
- Save generated notes, summaries, plans, or intermediate artifacts.
- Update project data files after analyzing source inputs.

## Security boundary
- Access is strictly limited to `wence_data/project`.
- Any path outside this root is rejected.
