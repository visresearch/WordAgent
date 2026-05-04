## Default Recommended Writing Style

Use this style unless the user explicitly requests another format.

### Layout
1. Keep layout clean and consistent.
2. Use bold headings and unified body formatting.
3. Preserve clear heading hierarchy: title → section → subsection → body.
4. Never use `\n` inside run.text. One line = one paragraph.
5. For blank lines, insert empty paragraph: `{"pStyle": "", "runs": []}`.

### Recommended Style IDs
| ID | Purpose |
|----|---------|
| `pS_1` | Centered main title (1.5 line spacing) |
| `pS_2` | Section heading (Heading 1, 1.5 spacing) |
| `pS_4` | Subsection heading (Heading 2, 1.5 spacing) |
| `pS_3` | Body text (justified, first-line indent, 1.5 spacing) |
| `pS_5` | Table cell (centered, single spacing) |
| `pS_6` | Figure/chart caption (centered, single spacing) |
| `rS_1` | Heading font (bold) |
| `rS_2` | Body font |
| `rS_3` | English/number in headings (Times New Roman, bold) |
| `rS_4` | English/number in body (Times New Roman) |
| `rS_5` | Caption font (黑体, 五号) |

### Default Style Map
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

### Key Rules
- `styles` is mandatory for `generate_document`
- Each style value must be an array (not object)
- Every `pStyle/rStyle` used must be defined in `styles`
- Section headings (一、) use `pS_2`; subsections (1.1, 1.2) use `pS_4`
- English/numbers in headings → separate run with `rS_3`
- English/numbers in body → separate run with `rS_4`
- Figure captions: `图X 描述` with `pS_6` + `rS_5`
