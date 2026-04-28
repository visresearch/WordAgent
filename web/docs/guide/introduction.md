# 项目介绍

**文策AI（Word Agent）** 是一个基于（多）智能体的 AI 辅助写作系统，用户在办公软件（如 WPS、Microsoft Word）中安装加载项后，可以通过自然语言与 AI 智能体进行交互，获取 **写作建议**、**内容生成**、**结构优化** 等服务。

> 文策AI（Word Agent）：让写作有策略，让表达更智能

![文策AI](/WenceAI_small.png)

## 核心优势

### 跨平台适配

以国民级办公软件为载体，类 Copilot 风格的 Word 加载项，让普通用户无门槛获得优质的 AI 写作辅助体验，同时支持 Windows 和 Linux 系统。

### 原生富文本生成

对比常见的 AI 写作工具，文策 AI 智能体能够理解 Word 文章结构，能够自主联网搜集资料信息，生成符合 Word 文档结构的内容，支持文档样式、段落编辑（标题、正文、加粗、字体、缩进、行距等）。

### 多智能体协作

多智能体扮演不同 **专家角色**，以生成有深度的长文章为目标，协同完成写作任务。

### 自由开放

支持自定义 API 或本地服务，兼容世界上大多数主流的 LLM 服务商，用户可以根据自己的需求选择不同的模型。

## 项目预览

| WPS 加载项界面 | 后端服务 QT 界面 |
|:--:|:--:|
| ![WPS加载项](/wps_addon.png) | ![QT界面](/pyQt.png) |

举个例子，以 WPS 为例，使用单智能体 agent 模式，用户在 WPS 加载项界面中输入"帮我把实习目的扩写成 5 点"，智能体会先调用 search_document 工具查询到实习目的所在段落的位置，然后调用 read_document 工具读取这个段落的内容并返回给智能体，智能体在获取到这个段落的内容后进行分析和理解，然后调用 delete_document 工具删除原来实习目的段落的内容，调用 generate_document 工具生成新的扩写后的内容。前端加载项会根据智能体返回用不同颜色批注渲染出修改前和修改后的内容，用户就可以清晰地看到智能体对文档所做的修改了。

![预览](/preview.png)

智能体在生成文字内容的同时还会生成内容对应的样式信息（如标题、正文、加粗、字体、缩进、行距等），前端加载项会根据这些样式信息将内容渲染成对应格式的 Word 文档呈现给用户。

除此之外，本项目还支持用户自定义工具的接入，用户可以通过配置 MCP 服务器的方式让智能体调用第三方 API 来增强智能体的能力。以**高德地图**和**可视化图表-MCP-Server**为例，用户输入"查询长沙未来五天的天气，绘制一个气温折线统计图，写一份天气预报文章"。智能体会调用高德地图 MCP 服务器进行查询长沙最近几天的气温数据，然后智能体会调用可视化图表-MCP-Server 这个 MCP 服务器生成一个折线统计图的图片 URL，把这张图片渲染在前端加载项界面中。

![MCP示例](/mcp_example.png)

## 快速开始

### 环境配置

- Node.js v22+
- Python 3.11+
- Win10/11、Ubuntu 22.04

### 构建前端加载项

```bash
# WPS Word 加载项
cd frontend/wps_word_plugin
pnpm install
pnpm build

# 或 Microsoft Word 加载项
cd frontend/microsoft_word_plugin
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
| WPS Office（Windows、Linux） | 12.1.25225 及以上 |
| Microsoft Word（Windows、Web） | 2019/2021 及以上 |

## 开发计划

- [x] 支持单智能体模式
- [x] 支持多智能体模式
- [x] 支持远程 MCP 服务器工具接入
- [x] 支持本地 MCP 服务器和 Skill 工具接入
- [x] 支持上下文压缩
- [x] 支持表格、插图、公式等复杂样式编辑（公式可读但不能生成）
- [x] 支持 WPS Word 桌面客户端
- [x] 支持 Microsoft Word 网页版
- [ ] 支持更多复杂样式编辑功能

## LLM API 适配情况

| 模型 | 状态 |
|------|------|
| Qwen 3.5 Plus | ✅ 运行稳定 |
| Qwen3 Max | ✅ 运行稳定 |
| GLM-5 | ✅ 运行稳定 |
| GPT 5.4 | ✅ 运行稳定 |
| MiniMax M2.5 | ✅ 运行稳定 |
| Step 3.5 Flash | ✅ 运行稳定 |
| DeepSeek v3.2 | ✅ 运行稳定 |
| Claude Sonnet/Opus | ✅ 运行稳定 |
| Kimi K2.5 | ⚠️ 容易出现工具调用死循环 |
| Gemini 3.1 Pro | 🔲 待测试 |

本项目开发使用了部分[阿里云百炼](https://bailian.console.aliyun.com/)、[Openrouter](https://openrouter.ai/models?q=free)免费额度。

## 开源协议

本项目采用 [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0) 开源协议。
