# 常见问题

## 获取不到模型列表

- 检查 API Key 和 Base URL 是否正确，Base URL 应是 API 地址而不是服务商首页。
- DeepSeek 官方 API 请选择 **OpenAI 兼容** API 类型，Base URL 使用 `https://api.deepseek.com`。
- 确认服务商账户可用且仍有额度。
- 如果使用代理，请在 **设置 → 通用 → 网络代理** 中确认地址和端口。

详细配置见 [配置大模型服务](/guide/api-config)。

## 智能体没有生成文档

- 确认当前使用 **Agent** 模式；Ask 模式不会修改文档。
- 确认模型支持 Tool Calling，项目推荐 GPT 系列或 Qwen 系列；DeepSeek V4 Pro 也可按配置指南接入。
- 查看文策 AI 桌面程序日志，确认是否存在 API 或工具调用错误。
- 如果界面出现待确认操作，点击 **确认** 接受本轮原生修订，或点击 **取消** 拒绝修改。

## 温度和思考开关在哪里

Temperature 已从个性化页面移到 **设置 → 大模型 → 已添加模型右侧齿轮**，与 Top-p、Max Tokens 和 Reasoning Effort 一起按模型保存。修改后点击 **确定 → 保存设置**。

聊天输入区不再提供“允许思考”开关，推理由 Reasoning Effort 控制，默认 `medium`。`none` 表示请求关闭推理，是否支持取决于模型。详见 [模型参数面板](/guide/api-config#编辑-llm-模型参数)。

## 外部 Agent 无法调用文档 MCP

- 在文策 AI 桌面程序的 **MCP 服务器** 页面点击 **运行**，连接地址使用 `http://127.0.0.1:3880/mcp/`，以界面显示的实际地址为准。
- 保持目标文档的文策 AI 加载项侧栏打开。服务运行与侧栏连接是两个条件，缺少侧栏时文档工具无法执行。
- WPS 与 Microsoft Word 同时连接时，工具参数需指定 `host: "wps"` 或 `host: "word"`。
- Microsoft Word 只保留目标文档的侧栏，`docId` 使用 `0`。

Codex 配置与工具说明见 [外部 Agent 文档 MCP Server](/guide/mcp-server)。

## 生成过程卡住或上下文过长

- 点击停止按钮结束当前任务，再缩小处理范围或新建会话。
- 长文任务建议拆成“生成大纲 → 分节写作 → 总体审阅”等多个 Agent 对话步骤。
- 暂时关闭不需要的 MCP Server 和 Skill，减少上下文与工具数量。

## 加载项在 Word 中不显示

- 确认文策 AI 后端仍在运行。
- WPS 用户重新执行 [WPS 加载项安装](/guide/wps-plugin)，并重启 WPS。
- Microsoft Word 用户确认 HTTPS 服务、自签名证书和 `manifest.xml` 均已配置，参考 [Microsoft Word 加载项](/guide/msword-plugin)。

## macOS 阻止打开 WenCe AI

当前 macOS 应用通过 GitHub Release 分发。请在 Finder 中右键 **WenCe AI.app → 打开**；仍被阻止时，到 **系统设置 → 隐私与安全性** 中允许打开。请确认下载的是 Apple Silicon 对应的 `wence_ai-macos-arm64.dmg` 或 `.app.zip`。

## Skill 上传提示同名

同名 Skill 不会被覆盖。请先备份需要保留的内容，再删除已有 Skill，然后重新上传。也可以点击 Skill 卡片上的文件夹按钮直接打开其目录。

## 如何反馈其他问题

请在 [GitHub Issues](https://github.com/visresearch/WordAgent/issues) 提交问题，并附上系统、办公软件版本、模型名称、复现步骤和脱敏后的日志。
