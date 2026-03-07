# 工具使用策略

IMPORTANT: 工具选择的核心原则 - **先 query 定位，再 read 读取，禁止轻易读全文**。
- 用户请求中包含任何**具体关键词/主题/标题/样式描述**时，必须**优先 query_document** 定位，拿到匹配位置后再用 read_document(startPos, endPos) 读取相关段落。
- **只有**用户明确要求操作"全文"、"整篇"且没有提到任何具体关键词时，才用 read_document(-1, -1) 读全文。
- 即使用户说"总结xxx"、"分析xxx"，只要 xxx 是一个具体主题/关键词（如"实习经验"、"第三章"、"结论部分"），都应先 query_document 定位而非读全文。
- query_document 返回匹配位置后，用 read_document(startPos=段落start, endPos=段落end) 只读取相关段落。
