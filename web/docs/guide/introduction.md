# 项目介绍

**文策AI（Word Agent）** 是一个基于（多）智能体的 AI 辅助写作系统。用户在办公软件（如 WPS、Microsoft Word）中安装加载项后，可以通过自然语言与 AI 智能体交互，获取**写作建议**、**内容生成**、**结构优化**等服务。

> 文策AI（Word Agent）：让写作有策略，让表达更智能

![文策AI](/WenceAI_small.png)

## 项目概述

本项目采用 FastAPI 构建后端 API，前端加载项与后端使用流式接口通信，使前端能够实时展示 LLM 输出内容。前端采用 Vue3 和 JavaScript 开发，核心是 DocxJson 双向转换模块，能将带格式的 Word 文档内容与 JSON 格式互相转换。

后端基于 langchain 和 langgraph 实现智能体设计与协作，使用 chatOpenAI 接口完成 SSE 流式输出与工具调用，并使用 pySide6 提供简易后端服务界面，方便安装加载项与查看日志。

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

1. **跨平台适配**：类 Copilot 风格的 Word 加载项，支持 Windows 与 Linux。
2. **原生富文本**：理解 Word 结构并生成符合文档样式的内容。
3. **多智能体协作**：多专家角色协同生成高质量长文。
4. **自由开放**：支持自定义 API 或本地服务，兼容主流 LLM 服务商。

## 项目预览

| WPS 加载项界面 | 后端服务 QT 界面 |
|:--:|:--:|
| ![WPS加载项](/wps_addon.png) | ![QT界面](/pyQt.png) |

## 使用示例

**单智能体（Single Agent）模式**：用户输入“帮我把实习目的扩写成 5 点”。智能体按“定位 → 读取 → 理解 → 编辑”的流程完成任务：先调用 `search_document` 定位段落，再调用 `read_document` 读取内容；分析理解后调用 `delete_document` 删除原内容，最后调用 `generate_document` 生成新内容。前端加载项以不同颜色批注渲染修改前/修改后的内容。

![单智能体示例](/preview2.png)

**多智能体（Multi Agent）模式**：用户请求写一篇长篇小说并绘制插图时，规划智能体编排流程，研究智能体搜集资料与生成插图，大纲与写作智能体完成文章内容，审阅智能体检查并提出修改建议。

![多智能体示例-1](/preview3.png)

![多智能体示例-2](/preview4.png)

> 注意：多智能体模式更适合长文写作，能提升结构一致性，但工具调用能力略弱于单智能体模式。

## 可插拔扩展

项目支持两类可插拔扩展：**MCP Server** 与 **Skill**。

1）**MCP Server 示例**：用户配置 MCP 服务器后，智能体可调用第三方 API 来增强能力。以 **高德地图 MCP** 与 **可视化图表 MCP Server** 为例，用户输入“查询长沙未来五天的天气，绘制一个气温折线统计图，并写一份天气预报文章”，智能体会先获取气温数据，再生成折线图 URL，并将图片渲染在加载项界面中。

![MCP示例](/mcp_example.png)

2）**Skill 示例**：Skill 用于封装可复用的能力与流程（如提示词模板、工具调用编排、特定领域写作逻辑），加载后可按任务需求选择执行，提升稳定性。

![Skill示例](/skill-example.png)

## 系统架构

### Single Agent loop 架构

![单智能体架构](/single_agent_loop.png)

- **read_document**: 读取指定范围内容并转为 JSON。
- **generate_document**: 生成结构化 JSON 传给前端。
- **search_document**: 按格式或关键词定位段落。
- **web_fetch**: 抓取指定链接内容。

### Multi Agent 架构

![多智能体架构](/multi_agent.png)

- **planner agent**: 编排与调度工作流。
- **research agent**: 搜集资料信息。
- **outline agent**: 生成文章大纲。
- **writer agent**: 生成正文内容。
- **reviewer agent**: 审阅并提出修改建议。

## 快速开始

### 环境配置

- node v22.12.0
- wpsjs 2.2.3
- python 3.11.14
- Win10/11、Ubuntu 22.04

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
| WPS Office（Windows、Linux） | 12.1.2.24722 及以上 |
| Microsoft Word（Windows、Web） | 2019/2021 及以上 |

## 开发计划

- [x] 支持单智能体模式
- [x] 支持多智能体模式
- [x] 支持远程 MCP 服务器工具接入
- [x] 支持本地 MCP 服务器和 Skill 工具接入
- [x] 支持上下文压缩
- [x] 支持表格、插图、公式等复杂样式编辑（公式可读但不能生成）

## LLM API 适配情况

| 模型 | 状态 |
|------|------|
| Qwen 3.6 Plus | ✅ 运行稳定 |
| GLM-5.1 | ✅ 运行稳定 |
| GPT 5.4 | ✅ 运行稳定 |
| MiniMax M2.5 | ✅ 运行稳定 |
| Step 3.5 Flash | ✅ 运行稳定 |
| DeepSeek v4 pro | ✅ 运行稳定 |
| Claude Sonnet/Opus | ✅ 运行稳定 |
| MiMo-V2.5 | ✅ 运行稳定 |
| Gemini 3.1 Pro | 🔲 待测试 |

> 推荐使用 **GPT 系列** 模型，其次是 **Qwen 系列** 模型。

本项目开发使用了部分[阿里云百炼](https://bailian.console.aliyun.com/)、[Openrouter](https://openrouter.ai/models?q=free)免费额度。

## 开源协议

本项目采用 [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0) 开源协议。
