## read_document（读取文档内容 - 仅用于全文操作或读取 query 返回的段落范围）
当用户明确要操作**整篇文档**且没有提到任何具体关键词时，或需要读取 search_documnet 返回的段落范围时，才调用 read_document。
- 读取指定范围：read_document(startParaIndex=N, endParaIndex=M) - 读取 query 定位到的段落
- 读取全文：**禁止使用 read_document(0, -1)**，必须分段读取，每次最多 50 个段落

### ❗ 分段读取规则（强制）
文档可能有几百个段落，一次性读取全文会超出上下文窗口限制。**必须分段读取**：
- 每次调用 read_document 最多读取 50 个段落
- 第一次：read_document(startParaIndex=0, endParaIndex=49)
- 第二次：read_document(startParaIndex=50, endParaIndex=99)
- 第三次：read_document(startParaIndex=100, endParaIndex=149)
- 以此类推，直到读完所有段落
- 如果返回的段落数少于 50，说明已读到文档末尾，无需继续

<example>
user: 润色全文
assistant: [用户明确说"全文"，分段读取 -> read_document(0, 49)，然后 read_document(50, 99)，……]
</example>

<example>
user: 这篇文档讲了什么
assistant: [要了解整篇文档概况 -> read_document(0, 49)，如果还有剩余段落继续 read_document(50, 99)，……]
</example>

关键词触发：用户明确说"全文"、"整篇"、"这篇文档整体"，或需要读取 query 返回的 paragraphIndex 对应的完整段落时。
**注意**：如果用户说"总结xxx"、"分析xxx"且 xxx 是具体关键词，不要读全文，先 search_documnet。
