---
name: skill-creator
description: Create, adapt, review, validate, and package skills for WordAgent. Use when the user wants a new SKILL.md, wants to improve an existing skill, or needs a WordAgent-compatible skill folder or ZIP for installation.
---

# WordAgent Skill Creator

Create skills for WordAgent's real tools and loader. Keep the requested name when updating a skill.

## 1. Capture intent

Derive the triggers, inputs, outputs, constraints, edge cases, and target (Word document, project files, or both) from the conversation. Ask only for missing decisions that affect the result.

## 2. Inspect before editing

Use `list_file` and `read_file` to inspect an existing skill. Preserve useful assets and user instructions. Never silently replace a different skill with the same folder name.

## 3. Write for WordAgent

Create `skills/<skill-name>/SKILL.md` with `edit_file`. Use kebab-case for new names and English unless requested otherwise.

Frontmatter must contain only:

```yaml
---
name: skill-name
description: What the skill does and the user intents that should trigger it.
---
```

Put critical behavior in `SKILL.md` and keep it below 3000 characters. WordAgent loads at most 3000 characters per Markdown file and 12000 across the skill. It automatically loads companion `*.md` files in path order, so keep them short and consistent. Use `references/` for focused guidance, `scripts/` for deterministic logic, and `assets/` for templates or media.

Use only WordAgent tools: `load_skill_context`, `read_document`, `search_document`, `generate_document`, `delete_document`, `list_file`, `read_file`, `edit_file`, `python_repl`, `run_sub_agent`, and available MCP tools.

For Word editing skills, encode these rules explicitly:

- read existing content and obtain real paragraph IDs
- use `insertParaID=0` only for the first write to an empty document
- replace content with one `delete_document` call followed by `generate_document`
- do not repeat a deletion while Word UI confirmation is pending
- preserve unaffected content and styles

Do not depend on vendor-specific tools, artifact systems, CLI commands, or unavailable browser workflows.

## 4. Review and validate

Check that the description states capability and triggers, paths are relative, tool names are exact, and resources are necessary. Use `agents/*.md` as compact review criteria. For objective skills, optionally add 2-3 realistic cases to `evals/evals.json`.

Validate frontmatter, names, references, size limits, and tool compatibility. Use `python_repl` for small deterministic checks.

## 5. Package and hand off

When requested, create a ZIP containing exactly one top-level skill folder with `SKILL.md`. Exclude caches, temporary files, eval outputs, and secrets. Place it in the project sandbox. If the skill already exists, do not overwrite it; tell the user to delete the installed skill before uploading its replacement.

Summarize the created or changed files, validation performed, and any remaining assumptions.
