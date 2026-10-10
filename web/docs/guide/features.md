# 功能按钮说明

## 智能体模式选择

文策 AI 提供两种智能体模式：

| 模式 | 说明 | 适用场景 |
|---|---|---|
| **Agent模式** | 一个 AI 智能体独立完成任务 | 简单写作、内容修改、快速问答 |
| **Ask模式** | 单 AI 智能体具有文档读取工具，不具有输出工具 | 复杂问题解答、文档分析、资料查询 |

在聊天输入区的模式选择器中切换 Agent 或 Ask。

## 主要操作

- **发送按钮**：输入提问后点击发送，智能体开始处理
- **停止按钮**：如果智能体正在生成内容，点击停止可中断当前任务
- **设置按钮**：打开设置面板，管理模型、个性化、MCP、Skill、插件和数据
- **模型设置齿轮**：在大模型页面编辑当前模型的 Temperature、Top-p、Max Tokens 和 Reasoning Effort，详见 [模型参数](/guide/api-config#编辑-llm-模型参数)
- **确认 / 取消**：接受或拒绝本轮原生修订
- **新建会话**：开始新的上下文，保留已有会话历史

推理强度通过模型参数中的 **Reasoning Effort** 控制，聊天输入区不再提供“允许思考”开关。个性化页面用于编辑全局提示词和应用快速模板。

**设置 → 插件** 可安装或删除 OCR 等独立 Python 插件，也支持通过 GitHub 链接安装自定义插件。界面与操作步骤见 [插件管理](/guide/plugins)。

## 文档操作工具

智能体在工作过程中会自动调用工具，以下是各种模式智能体可用的工具列表：

| 工具 | 功能 | Agent | Ask |
|---|---|---|---|
| **read_document** | 读取文档中指定范围的内容 | ✅ | ✅ |
| **search_document** | 查询某种格式或文字信息的段落位置 | ✅ | ✅ |
| **generate_document** | 生成带格式的文档内容并插入到 Word 中 | ✅ | ❌ |
| **edit_document** | 按 `paraID` 替换单个段落正文并保留原 `pStyle` | ✅ | ❌ |
| **delete_document** | 删除 Word 中指定的段落 | ✅ | ❌ |
| **create_document** | 创建并打开新的空白 DOCX 文档 | ✅ | ❌ |
| **insert_break** | 在指定段落后插入换行、分页或分节符 | ✅ | ❌ |
| **mcp_tools** | 调用已启用的 MCP 服务器工具 | ✅ | 视配置而定 |
| **load_skill_context** | 加载已启用 Skill 的完整规则 | ✅ | ✅ |
| **list_file** | 列出任务文件 | ✅ | ✅ |
| **read_file** | 读取任务文件 | ✅ | ✅ |
| **edit_file** | 编辑任务文件（不修改 Word 正文） | ✅ | ✅ |
| **python_repl** | 运行 Python 代码 | ✅ | ❌ |


::: info 说明
这些工具由智能体自动调用，你无需手动操作。智能体会根据你的提问自动判断需要使用哪些工具。
:::

::: warning 当前版本说明
当前仅提供 Agent 和 Ask 两种模式。`edit_document` 用于 Agent 模式的单段落原位改写；Ask 模式不会生成或删除 Word 内容。
:::

## 外部 Agent 文档工具

在桌面程序的 **MCP 服务器** 页面点击 **运行**，Codex 等客户端即可通过 [文档 MCP Server](/guide/mcp-server) 调用 `read_document`、`search_document`、`edit_document`、`delete_document`、`generate_document`、`insert_break` 和 `create_document`。调用时需保持目标文档的加载项侧栏打开。
