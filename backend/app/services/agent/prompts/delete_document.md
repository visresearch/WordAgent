## delete_document

### 使用场景
delete_document 用于**删除 Word 文档中指定范围的段落**。前端会先用蓝色批注标记要删除的段落，等待用户确认后才正式执行删除。

### 非阻塞特性（重要）
- 本工具发送删除请求后**立即返回**，不会等待用户确认
- 你可以继续调用其他工具（如 generate_document），不需要等待删除完成
- 用户会在 agent 执行完毕后自行确认或取消删除

### 调用场景
- 用户明确要求删除某些段落、章节或内容
- 用户说"删掉这段"、"把XX部分去掉"、"移除这段内容"、"删除第X段"
- 配合 search_documnet 定位到目标段落后，删除匹配的段落

### 不应调用的情况
- 用户要求修改/润色/重写内容（应使用 generate_document）
- 用户只是查找/搜索内容（应使用 search_documnet）
- 用户没有明确的删除意图

### 参数说明
- `startParaIndex`（int）：起始段落索引（0-based），默认 0
- `endParaIndex`（int）：结束段落索引（0-based，含），-1 表示到文档结尾

### 典型用法
1. 用户说"删除第3段" → 先用 search_documnet 或 read_document 确认第3段位置 → `delete_document(startParaIndex=2, endParaIndex=2)`
2. 用户说"删除关于XX的那段" → 先用 `search_documnet(filters={regex: "XX", regexFlags: ""})` 定位 → 得到 paragraphIndex → `delete_document(startParaIndex=idx, endParaIndex=idx)`
3. 用户说"删除第2到第5段" → `delete_document(startParaIndex=1, endParaIndex=4)`

### 注意事项
- 删除操作需要用户在前端确认后才会执行，不会立即生效
- 用户可以取消删除操作
- 删除前建议先用 read_document 或 search_documnet 确认要删除的内容是否正确
- 本工具是非阻塞的，调用后可立即继续执行其他工具

### 配合 generate_document 修改内容
CRITICAL: 当用户要求**修改/润色/重写**已有段落时，需要 delete_document + generate_document 配合：
1. 先调用 `delete_document(startParaIndex, endParaIndex)` 标记删除旧段落（非阻塞，立即返回）
2. 紧接着调用 `generate_document(insertParaIndex=startParaIndex)` 插入修改后的新段落
3. 两个工具可以连续调用，不需要等待用户确认删除

<example>
user: 删掉第二段
assistant: [先 read_document 确认第二段内容 -> 确认后调用 delete_document(startParaIndex=1, endParaIndex=1)]
已标记待删除内容，请确认。
</example>

<example>
user: 把关于实习目的的段落删掉
assistant: [先 search_documnet(filters={regex: "实习目的", regexFlags: ""}) 定位 -> 得到 paragraphIndex -> 调用 delete_document]
已标记待删除的段落，请确认。
</example>

<example>
user: 润色第3段
assistant: [read_document 读取第3段 -> delete_document(2, 2) 删除旧段落 -> generate_document(insertParaIndex=2) 插入润色后新段落]
已为您润色并替换了第3段。
</example>
