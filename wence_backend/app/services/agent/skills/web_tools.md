## web_search
当用户需要查找**最新信息**、参考资料或你不确定的知识时，调用 web_search 进行网络搜索。
- 返回搜索结果摘要（标题、链接、描述）
- 搜索摘要本身已足够用于写作和生成文档
- 如果需要深入了解某条结果，可以尝试调用 web_fetch 获取完整内容

<example>
user: 帮我查一下2026年诺贝尔文学奖得主是谁
assistant: [调用 web_search("2026年诺贝尔文学奖得主")]
</example>

<example>
user: 写一篇关于量子计算最新进展的文章
assistant: [先调用 web_search("量子计算 最新进展 2026") 获取资料，再调用 generate_document 生成文档]
</example>

关键词触发：用户提到"搜索"、"查一下"、"上网找"、"最新"、"最近"或你缺乏相关知识时。

## web_fetch
当你需要获取**特定网页的完整内容**时，调用 web_fetch。
- 自动清洗 HTML，返回纯净正文
- 常与 web_search 配合使用：先搜索找到相关链接，再 fetch 获取详情

<example>
user: 帮我读一下这个链接的内容 https://example.com/article
assistant: [调用 web_fetch("https://example.com/article")]
</example>

关键词触发：用户提供了 URL 链接，或搜索结果不够详细需要深入阅读时。

IMPORTANT: web_fetch 只是**可选的补充步骤**，不是必须步骤。
- 如果 web_fetch 失败（403/超时等），不要反复重试，直接使用已有的搜索摘要继续任务
- 不要因为 fetch 失败就放弃生成文档或改变原始任务目标
- web_fetch 最多调用 1 次，失败后立即回到主任务流程
