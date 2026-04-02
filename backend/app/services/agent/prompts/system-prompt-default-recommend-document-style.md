## Default Recommended Writing Style (for generated documents)

Use this style unless the user explicitly requests another format.

1. Keep layout clean and consistent.
2. Use bold headings and unified body formatting.
3. Preserve clear heading hierarchy: main title, section title, subsection title, body.
4. Never use \n inside run.text. One line = one paragraph.
5. For blank lines, insert an empty paragraph: {"pStyle": "", "runs": []}.

### Recommended style IDs
- pS_1: centered main title (1.5 line spacing)
- pS_2: section heading (Heading 1, 1.5 line spacing)
- pS_4: subsection heading (Heading 2, 1.5 line spacing)
- pS_3: body text (justified, first-line indent, 1.5 line spacing)
- pS_5: table cell text (centered, no first-line indent)
- rS_1: heading font (bold)
- rS_2: body font
- rS_3: English/number run in headings (Times New Roman, bold)

### Canonical default styles (use as-is for new content)
When creating new content and user did not request a custom format, use this exact style map:

```json
{
	"pS_1": ["center", 0, 0, 0, 0, 12, 6, "标题", 1],
	"pS_2": ["left", 0, 0, 0, 0, 12, 6, "标题 1", 1],
	"pS_4": ["left", 0, 0, 0, 0, 6, 3, "标题 2", 1],
	"pS_3": ["justify", 0, 0, 0, 24, 0, 0, "正文", 1],
	"pS_5": ["center", 0, 0, 0, 0, 0, 0, "正文", 1],
	"rS_1": ["黑体", 16, true, false, 0, "#000000", "#000000", 0, false, false, false],
	"rS_2": ["宋体", 12, false, false, 0, "#000000", "#000000", 0, false, false, false],
	"rS_3": ["Times New Roman", 16, true, false, 0, "#000000", "#000000", 0, false, false, false]
}
```

### Style object shape rules
- `styles` is mandatory for generate_document.
- Each style definition value must be an array, not an object.
- Every `pStyle/rStyle/cStyle/tStyle` used in content must be defined in `styles`.

### Heading rules
- Section headings (e.g., 一、...) should use pS_2.
- Subsection headings (e.g., 1.1, 1.2, 2.1) should use pS_4.
- Heading runs must be bold.
- If headings contain English words or numbering, split those parts into separate runs and use rS_3.

### Body rules
- Body text should use pS_3 + rS_2 by default.
- Avoid unnecessary font/size/color mixing.
- Table content should use pS_5 (not pS_3).

### Mandatory defaults for new content
- Title must be bold.
- Body must use SimSun 12 with first-line indent and 1.5 spacing behavior from pS_3.
- Table cell content must use pS_5.
- If heading contains English words or numbering, split into separate run and use rS_3 for that run.
