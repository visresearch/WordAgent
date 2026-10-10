# 项目介绍

**文策AI（Word Agent）** 是一个基于智能体的 AI 辅助写作系统。用户在办公软件（如 WPS、Microsoft Word）中安装加载项后，可以通过自然语言与 AI 智能体交互，获取**写作建议**、**内容生成**、**结构优化**等服务。

::: info
如果 Windows 新版本 WPS 加载项出现运行卡死，可以在“设置 → 切换窗口管理模式”中改为多组件模式。详情请参考 [issue #1](https://github.com/visresearch/WordAgent/issues/1)。
:::

> 文策AI（Word Agent）：让写作有策略，让表达更智能

![文策AI](/banner.png)

## 项目概述

本项目采用 FastAPI 构建后端 API，前端加载项与后端使用流式接口通信，使前端能够实时展示 LLM 输出内容。前端采用 Vue3 和 JavaScript 开发，核心是 DocxJson 双向转换模块，能将带格式的 Word 文档内容与 JSON 格式互相转换。

后端基于 LangChain 和 LangGraph 实现智能体设计与协作，使用 OpenAI/Anthropic 兼容接口完成流式输出与工具调用。前端加载项通过 WebSocket 与后端通信，PySide6 桌面程序用于启动服务、安装加载项和查看日志。

为了让智能体能够生成**结构化 Word 文档**，项目中定义了一套接近 HTML/CSS 的 JSON Schema：

- **paragraphs**: 段落数组，包含多个 run 文本块
	- **pStyle**: 段落样式 ID（如标题1、正文等）
	- **runs**: 文本块数组（最小单位）
		- **text**: 文本内容
		- **rStyle**: 字符样式 ID（如加粗、红色等）
	- **paraIndex**: 段落索引，用于定位
	- **paraID**: 段落唯一标识，用于修改
- **styles**: 样式定义字典，包含段落样式与字符样式

## 核心优势

1. **跨平台适配**：后端应用支持 Windows、Linux 与 macOS，提供 WPS 和 Microsoft Word 加载项。
2. **原生富文本**：理解 Word 结构并生成符合文档样式的内容。
3. **智能体自主协作**：智能体能够理解任务目标和文档上下文，自主调用合适的工具完成写作与编辑任务。
4. **自由开放**：支持自定义 API 或本地服务，兼容主流 LLM 服务商。

## 项目预览

| WPS 加载项界面 | 后端服务 QT 界面 |
|:--:|:--:|
| ![WPS加载项](/wps_addon.png) | ![QT界面](/QtGUI.png) |

## 使用示例

**单智能体（Single Agent）模式**：用户输入“帮我把实习目的修改成 5 点”。智能体按“定位 → 读取 → 理解 → 编辑”的流程完成任务：先调用 `search_document` 定位段落，再调用 `read_document` 读取内容；分析理解后调用 `delete_document` 删除原内容，最后调用 `generate_document` 生成修改后的内容。WPS 加载项通过原生修订显示内容变更，并在修订批注中展示修改信息，方便用户确认或取消。

![文档生成与原生修订示例](/generate_document_2x.gif)

对于单个段落内的小范围修改，可以使用 `edit_document` 工具按段落 ID 直接替换内容，同时保留段落属性和段落 ID，尤其适合修改表格内容。

![段落编辑示例](/edit_document_2x.gif)

## 可插拔扩展

项目支持三类可插拔扩展：**MCP Server**、**Skill** 与 **Python 插件**。

1）**MCP Server 示例**：用户配置 MCP 服务器后，智能体可调用第三方 API 来增强能力。以 **高德地图 MCP** 与 **可视化图表 MCP Server** 为例，用户输入“查询长沙未来五天的天气，绘制一个气温折线统计图，并写一份天气预报文章”，智能体会先获取气温数据，再生成折线图 URL，并将图片渲染在加载项界面中。

![MCP示例](/mcp_example.png)

2）**Skill 示例**：Skill 用于封装可复用的能力与流程（如提示词模板、工具调用编排、特定领域写作逻辑），加载后可按任务需求选择执行，提升稳定性。

![Skill示例](/skill-example.png)

3）**Python 插件示例**：在 **设置 → 插件** 中安装 `wordagent-plugin-ocr`，可为无法直接接收图片的模型提供图片文字识别能力。插件使用独立运行环境，支持安装、删除和通过 GitHub 链接添加自定义插件，详见 [插件管理](/guide/plugins)。

## 模型参数设置

在 **设置 → 大模型** 中点击已添加模型右侧的齿轮，在当前页面编辑 **Temperature**、**Top-p**、**Max Tokens** 和 **Reasoning Effort**。参数按模型保存，对话使用当前所选模型的配置。

![模型参数编辑面板](/model_config.png)

默认最大输出为 `8192` Tokens，Reasoning Effort 默认为 `medium`。个性化页面的温度设置与聊天输入区的思考开关已移除，统一在 [模型参数面板](/guide/api-config#编辑-llm-模型参数) 中调整。

## 外部 Agent 接入

桌面程序新增 **MCP 服务器** 页面，Codex 等外部 Agent 可通过 `http://127.0.0.1:3880/mcp/` 调用 WPS / Microsoft Word 的文档工具。打开目标文档的加载项侧栏后，即可读取、搜索、编辑或生成文档内容。

![供外部 Agent 调用的 MCP Server](/mcp-server.png)

连接步骤、Codex 配置和工具说明见 [外部 Agent 文档 MCP Server](/guide/mcp-server)。

## 快速开始

### 环境配置

- node v22.12.0
- wpsjs 2.2.3
- python 3.11.14
- Windows 10/11、Ubuntu 22.04、macOS 10.15+

### 构建前端加载项

```bash
cd frontend/wps_word_plugin       # WPS Word加载项
cd frontend/microsoft_word_plugin # 或 Microsoft Word 加载项
pnpm install
pnpm build
```

### 运行后端服务

```bash
cd backend
uv run python main.py
```

## 支持的办公软件

| 办公软件 | 支持版本 |
|---------|---------|
| WPS Office（Linux） | 12.1.2.24722 及以上 |
| WPS Office（Windows） | 12.1.0.28043 以下 |
| Microsoft Word（Windows、Web） | LTSC 2024 及以上，需支持 WordApi 1.6 或以上 |

## 开发计划

- [x] 支持单智能体模式
- [x] 支持远程 MCP 服务器工具接入
- [x] 支持本地 MCP 服务器和 Skill 工具接入
- [x] 通过文档 MCP Server 供外部 Agent 调用 WPS / Microsoft Word 工具
- [x] 支持按模型设置生成参数和推理强度
- [x] 支持上下文压缩
- [x] 支持长短期记忆
- [x] 支持表格、插图、公式等复杂样式编辑（公式可读但不能生成）
- [ ] 不局限于 localhost，支持局域网访问和云端部署

## LLM API 适配情况

| 模型 | 状态 |
|------|------|
| Qwen 3.6 Plus | ✅ 运行稳定 |
| GLM-5.1 | ✅ 运行稳定 |
| GPT 5.4 | ✅ 运行稳定 |
| MiniMax M2.5 | ✅ 运行稳定 |
| DeepSeek V4 Pro | ✅ 运行稳定 |
| Claude Sonnet/Opus | ✅ 运行稳定 |
| MiMo-V2.5 | ✅ 运行稳定 |

> 项目推荐使用 **GPT 系列**，其次是 **Qwen 系列**，详情见 [测评文档](https://github.com/visresearch/WordAgent/blob/master/backend/evaluation/README.md)。本指南以 DeepSeek V4 Pro 展示 [模型配置步骤](/guide/api-config)。

本项目开发使用了部分[阿里云百炼](https://bailian.console.aliyun.com/)、[Openrouter](https://openrouter.ai/models?q=free)免费额度。

## 开源协议

本项目采用 [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0) 开源协议。
