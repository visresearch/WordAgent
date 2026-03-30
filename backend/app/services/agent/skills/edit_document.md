## edit_document

### 最小改动原则（最高优先级）

CRITICAL: edit_document 用于编辑 Word 文档，支持删除、插入、替换三种模式。你必须只提交需要变动的内容，绝不能把未修改的原文重复输出。

### 长内容分批策略（推荐）

- 当目标 JSON 很长、一次 tool call 容易失败时，可分批多次调用 edit_document
- 每次只提交一个连续子范围或一个结构块（如一章/一节/一个表格）
- 多次调用时保持 paraIndex 与内容顺序一致，避免前后覆盖

### 调用前硬性校验（必须）

在调用 edit_document 之前，先逐项自检：
- delete-only：只能传 `startParaIndex/endParaIndex` 或 `deleteRanges`，不要传 `document`
- insert/replace：`document.styles` 必填，且必须覆盖所有样式引用（pStyle/rStyle/cStyle/tStyle）
- insert/replace：`document.paragraphs` 的每个段落都必须有 `paraIndex`
- insert/replace：若包含 `tables`，每个表格也应提供 `paraIndex`
- 任一项不满足时，先修正参数，再调用工具

错误示例（禁止）：
- `edit_document(document={"paragraphs":[...],"tables":[]})`  // 缺少 `styles`，会触发校验错误

### 三种调用模式（强制）

1) 仅删除（delete-only）
- 适用：用户明确要求“删除/删掉/移除”某段内容
- 参数：
  - 连续删除：`startParaIndex`, `endParaIndex`（可省略 end，默认等于 start）
  - 离散删除：`deleteRanges=[{startParaIndex,endParaIndex}, ...]`
- 不传 `document`

2) 仅插入（insert-only）
- 适用：用户要求“新增一段/写一篇新文档/追加表格”
- 参数：只传 `document`
- `document.paragraphs` 中每个段落都必须提供 `paraIndex`（目标写入位置）

3) 替换（replace，推荐）
- 适用：用户要求“修改/润色/重写/翻译/扩写/缩写”已有内容
- 参数：同时传 `startParaIndex`, `endParaIndex`, `document`
- 并确保 `document.paragraphs` 中每个段落都带 `paraIndex`
- 含义：先标记删除旧段落，再在原位置插入新内容（一次工具调用完成）

### 修改已有内容的标准流程

1. 先用 `read_document` 或 `search_documnet` 定位并读取目标段落
2. 计算目标范围 `startParaIndex ~ endParaIndex`
3. 调用 `edit_document(startParaIndex, endParaIndex, document)` 完成替换

### 表格修改规则（强制）

- 修改已有表格时，同样使用替换模式：
  - 先从 `read_document` 结果中拿到表格 `paraIndex` 与 `endParaIndex`
  - 调用 `edit_document(startParaIndex=paraIndex, endParaIndex=endParaIndex, document=...)`
  - 并确保插入段落都带目标 `paraIndex`
- 如果不删除旧表格直接插入新表格，会出现嵌套/结构异常风险。

### 严禁行为

- 修改已有内容时输出全文（会导致重复）
- 用户只要求新增一段时输出整篇文档
- 插入/替换时段落缺少 `paraIndex`

### 使用场景

- 需要“编辑文档内容”时优先使用 edit_document：删除、插入、替换都用它
- 用户明确要求写文档/报告/文章时，必须调用 edit_document（insert-only）输出到 Word
- 不允许把长文直接输出在对话中替代工具调用

### 不应调用的情况

- 仅需搜索/定位内容（用 `search_documnet`）
- 仅需读取内容（用 `read_document`）
- 闲聊问答或纯解释

### 格式规则

- `document` 必须符合新版 schema：
  - `pStyle/rStyle/cStyle/tStyle` 必须是样式引用 ID（如 `pS_1`）
  - 顶层必须包含 `styles`，覆盖所有被引用样式
  - 参数必须是对象：`edit_document({"document": {...}})`，不能传 JSON 字符串
- `document.paragraphs` 中每个段落都要带 `paraIndex`
- 若包含 `document.tables`，每个表格建议显式带 `paraIndex`
- 每行内容独立为一个 Paragraph，禁止在 `run.text` 使用 `\n`
- 需要空行时，使用空段落：`{"pStyle": "", "runs": []}`
- **styles 字段格式（强制）**：`document.styles` 中每个样式的值必须是数组，不能是对象
  - 正确：`{"pS_1": [{"name": "标题"}], "rS_1": [{"fontName": "宋体", "fontSize": 16}]}`
  - 错误：`{"pS_1": {"name": "标题"}, "rS_1": {"fontName": "宋体", "fontSize": 16}}`

### 示例

<example>
user: 润色第3段
assistant: [先 read_document 读取第3段 -> 调用 edit_document(startParaIndex=2, endParaIndex=2, document={paragraphs:[{paraIndex:2,...}],...})]
已为您润色并替换第3段。
</example>

<example>
user: 在第二段后面增加一段关于中国态度的内容
assistant: [调用 edit_document(document={paragraphs:[{paraIndex:2,...}],...})]
已为您添加新段落。
</example>

<example>
user: 删除第2到第5段和第9段
assistant: [调用 edit_document(deleteRanges=[{startParaIndex:1,endParaIndex:4},{startParaIndex:8,endParaIndex:8}])]
已标记待删除内容，请确认。
</example>

<example>
user: 帮我写一篇关于AI的报告
assistant: [调用 edit_document(document={paragraphs:[{paraIndex:0,...},...],...})]
已为您生成报告文档。
</example>
