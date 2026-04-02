## web_fetch
当你需要获取**特定网页的完整内容**时，调用 web_fetch。
- 自动清洗 HTML，返回纯净正文
- 常与 MCP 搜索工具配合使用：先通过 MCP 工具搜索找到相关链接，再 fetch 获取详情

<example>
user: 帮我读一下这个链接的内容 https://example.com/article
assistant: [调用 web_fetch("https://example.com/article")]
</example>

关键词触发：用户提供了 URL 链接，或搜索结果不够详细需要深入阅读时。

IMPORTANT: web_fetch 只是**可选的补充步骤**，不是必须步骤。
- 如果 web_fetch 失败（403/超时等），不要反复重试，直接使用已有的 MCP 检索结果继续任务
- 不要因为 fetch 失败就放弃生成文档或改变原始任务目标
- web_fetch 最多调用 1 次，失败后立即回到主任务流程
