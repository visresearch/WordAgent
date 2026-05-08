## list_file Usage Policy

- Start with `list_file(path=".")` when you need to discover project files.
- Prefer non-recursive listing first; use `recursive=true` only when needed.
- Narrow the path (for example `uploads`, `skills`, `temp`) before deep listing.
- Do not guess file names when you can verify with `list_file` first.
