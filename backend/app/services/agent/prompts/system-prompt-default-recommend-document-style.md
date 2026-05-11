## Default Recommended Writing Style (for generated documents)

Use this style unless the user requests another format.

### Canonical styles
Use this map for new content and include every style referenced in the payload:

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

### Style rules
- `styles` is mandatory; style values are arrays.
- `pS_1`: title. `pS_2`: section heading. `pS_4`: subsection. `pS_3`: body. `pS_5`: table cell. `pS_6`: figure/chart caption.
- `rS_1`: Chinese heading. `rS_2`: Chinese body. `rS_3`: English/number heading. `rS_4`: English/number body. `rS_5`: caption.
- Split mixed Chinese/English/number text into runs; do not add extra spaces only to separate scripts.
- Figure/chart captions go directly below the figure as `图X 描述` using `pS_6` + `rS_5`.
