# 快速开始

## 1. 下载并启动文策 AI

普通用户前往 [GitHub Releases](https://github.com/visresearch/WordAgent/releases) 下载发行版：

| 平台 | 推荐下载 |
|---|---|
| Windows 10/11 | `wence_ai-windows-x86_64-installer.exe` |
| Ubuntu / Debian | `wence_ai-linux-x86_64.deb` |
| macOS Apple Silicon | `wence_ai-macos-arm64.dmg` |

- WPS Office Linux 版本 12.1.2.24722及以上、Windows 版本 12.1.0.28043 以下
- Microsoft Word（Windows、Web）版本 LTSC 2024及以上(wordAPI 1.6及以上)

安装并启动 **WenCe AI / 文策 AI**。免安装包、Intel Mac 和源码运行方式请查看 [安装方式](/guide/installation)。

## 2. 加载 Word 插件

根据使用的办公软件选择对应说明：

- [安装 WPS Word 加载项](/guide/wps-plugin)：适用于 Windows、Linux 的 WPS Office。
- [启动 Microsoft Word 加载项](/guide/msword-plugin)：适用于 Windows、macOS 和 Word 网页版。

安装成功后，文策 AI 会显示在 Word 侧边栏中。

## 3. 配置 DeepSeek V4 Pro

1. 打开侧边栏的 **设置 → 大模型**。
2. 添加 `DeepSeek` 提供商，填写官方 API Key，Base URL 设为 `https://api.deepseek.com`，API 类型选择 **OpenAI 兼容**。
3. 获取模型列表，添加并启用 **DeepSeek V4 Pro**。
4. 保存设置并返回聊天页选择该模型。

完整字段说明见 [配置大模型服务](/guide/api-config)。

## 4. 开始第一个任务

在输入框中选择 **Agent** 模式，然后尝试：

```text
读取当前文档，为文章补充一个结构清晰的总结，并保持现有文档风格。
```

涉及文档修改时，前端会展示待确认操作。确认后才会将内容写入 Word。

## 5. 继续配置

- [如何提问](/guide/how-to-ask)
- [功能与 Agent 模式](/guide/features)
- [个性化配置](/guide/personalization)
- [MCP 服务器](/guide/mcp)
- [Skill 配置](/guide/skills)
