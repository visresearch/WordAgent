# Contributing to WordAgent

Thank you for your interest in contributing to WordAgent!

WordAgent is an open-source AI writing agent for WPS Office and Microsoft Word. We welcome all kinds of contributions, including bug fixes, new features, documentation improvements, built-in Skills, model integrations, UI enhancements, and test cases.

Please read this guide before submitting an Issue or Pull Request.

## Ways to Contribute

You can contribute to the project in the following ways:

* Report bugs
* Suggest new features
* Improve the English or Chinese documentation
* Fix backend or frontend issues
* Add integrations for model providers
* Improve Single Agent or Multi Agent workflows
* Submit new built-in Skills
* Add test cases
* Improve the WPS or Microsoft Word add-ins
* Improve the packaging process for Windows, Linux, or macOS

## Development Environment

We recommend the following environment:

* Python 3.11 or later
* Node.js 22 or later
* uv
* pnpm 10
* Git
* WPS Office or Microsoft Word for testing add-in functionality

Clone the repository:

```bash
git clone https://github.com/visresearch/WordAgent.git
cd WordAgent
```

We recommend forking the repository first and creating a development branch from your fork.

## Branch Naming

Create a feature branch from the latest `master` branch:

```bash
git checkout master
git pull origin master
git checkout -b feat/your-feature
```

We recommend the following branch prefixes:

| Type | Example |
| --- | --- |
| Feature | `feat/add-model-provider` |
| Bug fix | `fix/skill-loading-error` |
| Documentation | `docs/update-installation-guide` |
| Refactoring | `refactor/agent-runtime` |
| Tests | `test/add-skill-tests` |
| Built-in Skill | `skill/academic-writing` |
| Build and CI | `build/update-pyinstaller` |

Avoid developing directly on the `master` branch.

## Backend Development

Go to the backend directory:

```bash
cd backend
```

Install production and development dependencies:

```bash
uv sync --extra dev
```

Start the backend:

```bash
uv run python main.py
```

Run tests:

```bash
uv run pytest
```

Run Ruff:

```bash
uv run ruff check .
```

Automatically fix issues that Ruff can handle:

```bash
uv run ruff check . --fix
```

Check code formatting:

```bash
uv run black --check .
```

Automatically format the code:

```bash
uv run black .
```

Run type checks:

```bash
uv run mypy app
```

Before submitting backend changes, run at least:

```bash
uv run ruff check .
uv run black --check .
uv run pytest
```

### Python Code Requirements

* Add type annotations to new public functions and methods whenever practical.
* Avoid unnecessary mutable global state.
* Keep asynchronous call chains asynchronous, and avoid long-running blocking operations in the event loop.
* Prefer explicit data models for tool inputs and outputs.
* Do not hard-code API keys, access tokens, passwords, or user-specific paths.
* New features should include appropriate error handling and logging.
* Do not change frontend-backend communication fields casually. If a change is necessary, update both frontends accordingly.
* Explain the purpose of new dependencies and avoid introducing unnecessarily large packages.

## WPS Add-in Development

Go to the WPS add-in directory:

```bash
cd frontend/wps_word_plugin
```

Install dependencies:

```bash
pnpm install
```

Start the development server:

```bash
pnpm dev
```

Build the add-in:

```bash
pnpm build
```

Run lint checks:

```bash
pnpm lint
```

Format the code:

```bash
pnpm format
```

Do not manually modify build artifacts in the `dist/` directory.

## Microsoft Word Add-in Development

Go to the Microsoft Word add-in directory:

```bash
cd frontend/microsoft_word_plugin
```

Install dependencies:

```bash
pnpm install
```

Start the development server:

```bash
pnpm dev-server
```

Create a development build:

```bash
pnpm build:dev
```

Create a production build:

```bash
pnpm build
```

Run lint checks:

```bash
pnpm lint
```

Validate the add-in manifest:

```bash
pnpm validate
```

Format the code:

```bash
pnpm prettier
```

Start Microsoft Word debugging:

```bash
pnpm start
```

Stop debugging:

```bash
pnpm stop
```

## Frontend Contribution Requirements

* Features shared by WPS and Microsoft Word should behave consistently whenever practical.
* When changing the frontend-backend API, check whether both add-ins need corresponding updates.
* Include screenshots or screen recordings for UI changes.
* Do not include unrelated formatting changes.
* Do not manually edit generated files in `dist/`.
* Preserve the existing UI design and interaction style whenever practical.
* After changing an add-in manifest, run its corresponding validation command.

## Contributing a Built-in Skill

Built-in Skills should be stored in:

```text
backend/app/resources/builtin_skills/
```

Recommended structure:

```text
builtin_skills/
├── manifest.json
└── academic-writing/
    ├── SKILL.md
    ├── examples.md
    └── terminology.md
```

At runtime, built-in Skills are synchronized to the shared user Skill directory:

```text
wence_data/project/skills/
```

### Skill Directory Naming

Skill directory names must meet the following requirements:

* Use lowercase English letters.
* Use `kebab-case`.
* Keep the name stable after release.
* Do not use spaces or special characters.
* Choose a name that clearly describes the Skill's purpose.

Recommended:

```text
academic-writing
humanizer-zh
technical-report
meeting-summary
```

Not recommended:

```text
Skill 1
new_skill
test
My Skill
```

### SKILL.md Format

Every Skill must contain a `SKILL.md` file:

```markdown
---
name: Academic Writing
description: Write, expand, and refine academic papers, research reports, and related content.
---

# Academic Writing

## Use Cases

Use this Skill when the user needs to write academic papers, research reports, experimental analyses, or related formal content.

## Workflow

1. Understand the user's research topic and writing requirements.
2. Analyze the current document structure.
3. Conduct research first when information is missing.
4. Generate well-structured content with complete reasoning.
5. Check terminology, logic, and formatting for consistency.

## Constraints

- Do not fabricate experimental data or references.
- Clearly identify uncertain information.
- Maintain accurate and objective academic language.
```

### Skill Contribution Requirements

* A Pull Request should generally add or modify only one Skill.
* The `description` should clearly identify the triggering scenarios instead of providing only a broad overview.
* A Skill should provide an actionable workflow and explicit constraints.
* Move lengthy examples, glossaries, and reference material into separate Markdown files.
* Do not include API keys, user data, or private information.
* Skills containing executable Python, Shell, or JavaScript scripts are not accepted by default.
* Before including third-party content, ensure that its license permits redistribution and retain any required notices.
* When modifying a built-in Skill, update its version number in `manifest.json` accordingly.
* Do not overwrite or delete locally created user Skills.
* Test Skill discovery, activation, deactivation, and context-loading behavior.

When submitting a Skill, include the following information in the Pull Request:

1. The purpose of the Skill.
2. Applicable scenarios.
3. Triggering examples.
4. How it was tested.
5. Content sources and licenses.
6. Whether it will overwrite an existing Skill.

## Commit Guidelines

We recommend using the Conventional Commits format:

```text
<type>(<scope>): <description>
```

Common types:

| Type | Purpose |
| --- | --- |
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation change |
| `refactor` | Code refactoring that does not change behavior |
| `test` | Test-related change |
| `style` | Formatting-only change |
| `build` | Build system or dependency change |
| `ci` | CI workflow change |
| `chore` | Other maintenance work |

Examples:

```text
feat(skill): add built-in academic writing skill
fix(agent): prevent disabled skills from loading
docs: add contribution guide
refactor(frontend): unify skill settings components
test(skill): add built-in skill synchronization tests
```

Commit messages should be concise, specific, and describe the actual change.

## Submitting a Pull Request

Before submitting, ensure that your branch is based on the latest `master`:

```bash
git fetch upstream
git rebase upstream/master
```

Push your branch:

```bash
git push origin feat/your-feature
```

Then create a Pull Request targeting WordAgent's `master` branch.

### Pull Request Contents

Include the following in your Pull Request:

* The purpose and background of the change.
* The main implementation approach.
* Test methods and results.
* Affected platforms, such as Windows, Linux, macOS, WPS, or Microsoft Word.
* Screenshots or screen recordings for UI changes.
* Related Issues, such as `Closes #123`.
* The reason for any new dependencies.
* Any potential compatibility impact.

Recommended Pull Request description:

```markdown
## Changes

Briefly describe the problem addressed by this change.

## Implementation

Describe the main approach and key changes.

## Testing

- [ ] Backend tests pass
- [ ] Ruff checks pass
- [ ] Black formatting checks pass
- [ ] WPS add-in builds successfully
- [ ] Microsoft Word add-in builds successfully
- [ ] Tested in the actual office application

## Scope

Describe the affected modules and platforms.

## Screenshots

If the change affects the UI, include screenshots or a screen recording.

## Related Issue

Closes #123
```

### Pull Request Checklist

Before submitting, confirm that:

* [ ] The changes are consistent with the Pull Request's stated purpose.
* [ ] No API keys, passwords, or other sensitive information are included.
* [ ] No unrelated generated files are included.
* [ ] Relevant documentation has been updated.
* [ ] Applicable tests and checks have been run.
* [ ] New code includes appropriate error handling.
* [ ] Frontend-backend API changes have been synchronized.
* [ ] Shared WPS and Microsoft Word functionality has been checked for consistency.
* [ ] New third-party content complies with its license.
* [ ] Commit messages are clear and specific.

## Submitting an Issue

### Bug Reports

A bug report should include as much of the following information as possible:

* WordAgent version.
* Operating system and version.
* WPS Office or Microsoft Word version.
* Python and Node.js versions.
* Model and API provider used.
* Complete reproduction steps.
* Expected behavior.
* Actual behavior.
* Relevant logs and error messages.
* Screenshots or screen recordings, when needed.

Before submitting logs, remove:

* API keys
* Access tokens
* Cookies
* User document content
* Personal information
* Sensitive local paths

### Feature Requests

A feature request should explain:

* The current problem.
* The intended use case.
* The proposed interaction.
* Modules that may be affected.
* Whether you are willing to help implement it.

## Dependency Changes

When adding or upgrading Python dependencies:

```bash
cd backend
uv add package-name
uv lock
uv sync --extra dev
```

Commit the relevant changes to:

```text
backend/pyproject.toml
backend/uv.lock
```

When updating frontend dependencies, use `pnpm` and commit the corresponding:

```text
package.json
pnpm-lock.yaml
```

Do not mix npm, Yarn, and pnpm, and do not refresh the entire lockfile unless necessary.

## Documentation Changes

The project includes English and Chinese README files as well as a separate documentation site.

When modifying user-visible functionality, check whether the following also need to be updated:

```text
README.md
README.zh-CN.md
web/docs/
```

When documenting commands, paths, or configuration, ensure that the documentation matches the actual code.

## Security Issues

Do not publish the following in a public Issue:

* Working API keys
* Credentials
* Exploit details for undisclosed vulnerabilities
* User documents containing personal data
* Other sensitive information

If you discover a security issue, use GitHub's private vulnerability reporting feature or contact the project maintainers.

## Code of Conduct

Be friendly, professional, and respectful.

We do not tolerate the following behavior:

* Personal attacks or discriminatory language.
* Malicious harassment of other participants.
* Deliberately submitting destructive code.
* Publishing another person's private information without authorization.
* Submitting large numbers of irrelevant Issues or Pull Requests.

Maintainers reserve the right to close Issues and Pull Requests that do not meet the project's goals, quality standards, or code of conduct.

## License

WordAgent is licensed under the Apache License 2.0.

By submitting code, documentation, or other content to this project, you agree to license your contribution under the Apache License 2.0 used by the project.

Thank you for contributing to WordAgent!
