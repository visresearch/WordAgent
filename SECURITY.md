# Security Policy

WordAgent processes documents, local files, model credentials, Skills, MCP
connections, and requests to third-party AI services. We take vulnerabilities
that could compromise these assets seriously and appreciate responsible reports
from the security community.

## Supported Versions

Security fixes are provided for the latest released version of WordAgent.

| Version | Security support |
| --- | --- |
| Latest release | Supported |
| `master` branch | Best effort; this is a development branch and may be unstable |
| Older releases | Not guaranteed; please upgrade before reporting |

Before submitting a report, please verify the issue against the latest release
or the current `master` branch when it is safe to do so.

## Reporting a Vulnerability

**Do not disclose a suspected security vulnerability in a public GitHub issue,
discussion, pull request, log, or chat transcript.**

Please report it privately through GitHub Private Vulnerability Reporting:

<https://github.com/visresearch/WordAgent/security/advisories/new>

If private vulnerability reporting is unavailable, use the contact information
on the [WordAgent About page](https://visresearch.github.io/WordAgent/guide/about.html)
to ask the maintainers for a private reporting channel. In that initial message,
do not include exploit details, credentials, private documents, or other
sensitive material.

For ordinary bugs and feature requests that have no security impact, use
[GitHub Issues](https://github.com/visresearch/WordAgent/issues).

## What to Include

A useful report should contain as much of the following information as possible:

- A clear description of the vulnerability and its potential impact.
- The affected WordAgent version or commit hash.
- The operating system and, when relevant, the WPS Office or Microsoft Word
  version.
- Whether the issue occurs in single-agent or multi-agent mode.
- Whether Skills, MCP servers, add-ins, model API credentials, local files, or
  document access are involved.
- Minimal, reproducible steps and any required configuration.
- A proof of concept, screenshots, or logs with all sensitive data removed.
- Any known preconditions, mitigations, or suggested fixes.

Never include real API keys, access tokens, private documents, personal data, or
unredacted logs. Use synthetic test data and placeholder credentials.

## Response Process

We aim to:

- Acknowledge a report within 3 business days.
- Provide an initial assessment within 7 business days.
- Keep the reporter informed when the status materially changes.
- Coordinate a fix and disclosure timeline based on severity, exploitability,
  and affected users.

These are response targets rather than guarantees. Complex issues or reports
involving upstream dependencies and third-party services may require more time.
We may request additional information or a reproducible test case. Once a fix is
available, we may publish a GitHub Security Advisory and credit the reporter if
they wish to be named.

Please keep the report confidential until the maintainers confirm that a fix or
mitigation is available and coordinated disclosure is appropriate.

## Security Testing Guidelines

Research performed in good faith is welcome when it is limited to systems,
accounts, documents, and credentials that you own or are explicitly authorized
to test. Please minimize collection, access, modification, and retention of
data, and stop testing if you encounter data belonging to another person.

Do not:

- Access or attempt to access another user's system, account, documents,
  credentials, or data.
- Perform denial-of-service, destructive, disruptive, or resource-exhaustion
  testing.
- Introduce malicious dependencies, Skills, plugins, packages, or supply-chain
  changes.
- Test third-party model providers, MCP services, WPS Office, Microsoft Office,
  or other external infrastructure without their explicit authorization.
- Use social engineering, phishing, spam, physical attacks, or credential
  stuffing.
- Publicly disclose an unpatched vulnerability or retain data beyond what is
  necessary to demonstrate the issue.

## In Scope

Examples of security issues that are generally in scope include:

- Arbitrary code or command execution through WordAgent.
- Path traversal, unsafe archive extraction, or unauthorized local-file access.
- Exposure of API keys, tokens, private document content, or other secrets
  caused by WordAgent.
- Authorization or isolation failures across users, sessions, agents, Skills,
  MCP connections, or document operations.
- Add-in vulnerabilities that allow script execution or unauthorized document
  modification outside the user's confirmed action.
- Prompt-injection or tool-use behavior that reliably crosses an intended
  security boundary and causes unauthorized access or actions.
- Vulnerable update, packaging, installation, or dependency behavior that can
  be exploited in a supported WordAgent release.

## Out of Scope

The following are generally not treated as WordAgent security vulnerabilities
unless they demonstrate a concrete, reproducible security impact in WordAgent:

- Model hallucinations, low-quality output, formatting errors, or other
  nondeterministic model behavior.
- Prompt injection that does not cross a security boundary or perform an
  unauthorized action.
- Secrets that a user intentionally submits to a configured third-party model
  or MCP provider, when the behavior is clearly disclosed and expected.
- Vulnerabilities that exist only in unsupported versions and cannot be
  reproduced in a supported version.
- Findings produced only by automated scanners without a reproducible exploit
  or meaningful impact.
- Missing hardening recommendations, version banners, or best-practice headers
  without a practical attack scenario.
- Issues in third-party services or dependencies that do not create an
  exploitable condition in WordAgent. Report those issues to the relevant
  upstream project or provider.

## Disclosure and Remediation

Please allow a reasonable remediation period before publication. The project
may release a patch, document a mitigation, rotate affected secrets, notify
users, or coordinate with upstream maintainers as appropriate. Public advisories
will avoid exposing user data and will include affected versions and upgrade or
mitigation guidance whenever possible.

Thank you for helping keep WordAgent and its users safe.
