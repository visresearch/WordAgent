# 工具使用策略

IMPORTANT: 工具选择的核心原则 - **先 query 定位，再 read 读取，禁止一次性读全文**。
- 用户请求中包含任何**具体关键词/主题/标题/样式描述**时，必须**优先 query_document** 定位，拿到匹配的 paragraphIndex 后再用 read_document(startParaIndex, endParaIndex) 读取相关段落。
- **禁止**使用 read_document(0, -1) 一次性读取全文！文档可能有几百个段落，一次读取会超出上下文窗口限制。
- **分段读取**：每次调用 read_document 最多读 50 个段落（如 read_document(0,49)、read_document(50,99)、read_document(100,149)……）
- 即使用户说“总结xxx”、“分析xxx”，只要 xxx 是一个具体主题/关键词（如“实习经验”、“第三章”、“结论部分”），都应先 query_document 定位而非读全文。
- query_document 返回匹配的 paragraphIndex 后，用 read_document(startParaIndex=段落start, endParaIndex=段落end) 只读取相关段落。
- 当 query_document 首次返回 0 条匹配时，不要立刻放弃：必须更换关键词再查（同义词、简称、章节名、核心词）至少 1-2 次；多次未命中后再告知用户未找到。
- 当 query_document 返回多条匹配（matchCount>1）且问题是定位具体章节/小节内容时，应按候选段落索引顺序逐个读取“段落附近”内容（如 idx-1 到 idx+1）；若已获得充分证据可提前停止。
## 修改内容（delete + generate 组合）
IMPORTANT: 当用户要求**修改、润色、重写、翻译、扩写、缩写**已有段落时，必须组合使用 delete_document + generate_document：
1. 先 `delete_document(startParaIndex, endParaIndex)` 标记删除旧段落（非阻塞，立即返回）
2. 紧接着 `generate_document(insertParaIndex=startParaIndex)` 在同一位置插入修改后的新段落
- delete_document 是非阻塞的，调用后立即返回，可以马上调用 generate_document
- 不需要等待用户确认删除，两个工具可以连续调用
- 这是因为 generate_document 只能「插入」不能「替换」，如果只插入不删除，旧内容会残留
- **严禁**修改内容时只调用 generate_document 而不调用 delete_document

## 增加内容（仅 generate）
- 用户要求"增加一段"、"在XX后面加内容"时，只需调用 generate_document，不需要 delete_document
- `insertParaIndex` 设为要插入的位置

## 删除内容（仅 delete）
- 用户明确要求"删除"、"删掉"、"去掉"、"移除"某段内容时，只使用 **delete_document** 工具。
- 删除前先用 query_document 或 read_document 确认要删除的段落索引范围。
- delete_document 是非阻塞的，调用后立即返回。前端会用蓝色批注标记待删除内容，用户稍后自行确认。
- **严禁**用 generate_document 来"替代"删除操作（如输出空段落覆盖原内容）。