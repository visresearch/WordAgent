Submit document review results with score and feedback.

## Parameters
- `review` (object): Review result with:
  - `score` (int): Quality score 1-10
  - `feedback` (str): Detailed review feedback

## Scoring Guide
- **1-3**: Poor quality - major issues with content, structure, or writing
- **4-6**: Acceptable - some issues but usable with revisions
- **7-8**: Good quality - minor issues, ready with light editing
- **9-10**: Excellent - publication-ready

## Feedback Structure (Use This Format)
Structure your feedback in three sections:

```
Strengths:
- [2-3 specific positive points]

Issues:
- [2-4 specific problems with examples]

Suggestions:
- [2-3 actionable recommendations]
```

## Example
```json
{
  "score": 7,
  "feedback": "Strengths:\n- Clear structure with logical flow\n- Good use of section headings\n\nIssues:\n- Introduction too brief (1 paragraph)\n- Some paragraphs lack supporting evidence\n\nSuggestions:\n- Expand intro to 2-3 paragraphs\n- Add examples for each major claim"
}
```

## Important Notes
- Be constructive and specific
- Prioritize critical issues
- Provide actionable suggestions
- Do NOT modify the document
- Consider user's original requirements
