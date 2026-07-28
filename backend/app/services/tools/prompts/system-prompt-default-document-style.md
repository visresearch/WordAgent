## Default Document Style

Use these defaults only for newly generated content when the user, template, or loaded Skill does not prescribe another format. Existing or reference-document styles take precedence.

```json
{
  "pS_1": ["center", 0, 0, 0, 0, 12, 6, "标题", 1],
  "pS_2": ["left", 0, 0, 0, 0, 12, 6, "标题 1", 1],
  "pS_4": ["left", 0, 0, 0, 0, 6, 3, "标题 2", 1],
  "pS_3": ["justify", 0, 0, 0, 24, 0, 0, "正文", 1],
  "pS_5": ["center", 0, 0, 0, 0, 0, 0, "正文", 1],
  "pS_6": ["center", 0, 0, 0, 0, 0, 0, "正文", 1],
  "rS_1": ["黑体", 16, true, false, 0, "#000000", "#000000", 0, false, false, false],
  "rS_2": ["宋体", 12, false, false, 0, "#000000", "#000000", 0, false, false, false],
  "rS_3": ["Times New Roman", 16, true, false, 0, "#000000", "#000000", 0, false, false, false],
  "rS_4": ["Times New Roman", 12, false, false, 0, "#000000", "#000000", 0, false, false, false],
  "rS_5": ["黑体", 10.5, false, false, 0, "#000000", "#000000", 0, false, false, false]
}
```

- `pS_1`: document title; `pS_2`: top-level heading; `pS_4`: subsection; `pS_3`: body and ordinary blank paragraphs; `pS_5`: table cell; `pS_6`: figure caption.
- `rS_1/rS_3`: Chinese/English headings; `rS_2/rS_4`: Chinese/English body; `rS_5`: caption.
- Every paragraph, including `runs: []`, must use a defined non-empty `pStyle`. Every referenced style ID must exist in `document.styles`.
- Body English uses `Times New Roman`. Split mixed Chinese-English text into separate runs and keep the required Chinese font for Chinese runs.
- Put figure captions directly below the figure as `图X 描述` using `pS_6` and `rS_5`.
