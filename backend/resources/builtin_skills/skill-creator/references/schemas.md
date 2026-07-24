# Optional Test Schema

Store lightweight test cases in `evals/evals.json` only when objective checks add value.

```json
{
  "skill_name": "example-skill",
  "evals": [
    {
      "id": 1,
      "prompt": "A realistic user request",
      "expected_output": "The observable successful result",
      "files": [],
      "checks": [
        "Uses the required WordAgent workflow",
        "Produces the requested format",
        "Does not invent missing facts"
      ]
    }
  ]
}
```

Keep IDs unique. File paths are relative to the skill directory. Write checks as observable pass/fail statements; do not require private reasoning or unavailable execution transcripts.
