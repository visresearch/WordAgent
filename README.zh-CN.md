# Word Agent

![](./web/docs/public/banner.png)

<p align="center">
  <a href="backend/pyproject.toml"><img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white" alt="Python" /></a>
  <a href="backend/README.md"><img src="https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white" alt="FastAPI" /></a>
  <a href="https://www.langchain.com/"><img src="https://img.shields.io/badge/LangChain-Agent-1C3C3C?logo=chainlink&logoColor=white" alt="LangChain" /></a>
  <a href="frontend/microsoft_word_plugin/package.json"><img src="https://img.shields.io/badge/Node.js-v22%2B-339933?logo=node.js&logoColor=white" alt="Node.js" /></a>
  <a href="https://github.com/visresearch/WordAgent/releases"><img src="https://img.shields.io/github/v/release/visresearch/WordAgent?include_prereleases" alt="Version" /></a>
  <a href="https://github.com/visresearch/WordAgent/releases"><img src="https://img.shields.io/github/downloads/visresearch/WordAgent/total?logo=github&label=Downloads" alt="Release Downloads" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg" alt="License" /></a>
</p>

<p align="center">
  <a href="README.md">English</a> | 中文文档
</p>

> [!caution]
> 针对windows新版本wps插件运行卡死的问题，可以在“设置-切换窗口管理模式”中改为多组件模式来规避bug，详情请看[issue #1](https://github.com/visresearch/WordAgent/issues/1)

## 一、项目概述

本项目是一个基于智能体的AI辅助写作系统：文策AI，用户在 **办公软件(如WPS、Microsoft Word)** 中安装 **加载项** 后，可以通过自然语言与AI智能体进行交互，获取**写作建议**、**内容生成**、**结构优化**等服务。

> 文策AI（Word Agent）：让写作有策略，让表达更智能

对比市面上已有的AI辅助写作工具，文策AI的优势在于：

1. **支持多版本、跨平台适配**：以国民级办公软件为载体，类Codex风格Word加载项，让普通用户无门槛获得优质的AI写作辅助体验，并且同时支持Windows、Linux和macOS系统。
2. **原生富文本，支持文档样式、段落编辑**：对比常见的在Word中的AI写作工具，本项目智能体能够理解Word文章结构，能够自主联网搜集资料信息，生成符合Word文档结构的内容，能够根据用户需求进行文章结构修改和内容修改。
3. **高效编辑，支持智能体自主协作**：智能体能够理解任务目标和文档上下文，自主调用合适的工具完成写作与编辑任务。
4. **自由开放，支持自定义API或本地服务**：本项目使用的大模型服务APIKey来自于用户自己，目前支持世界上大多数主流的LLM服务商，用户可以根据自己的需求选择不同的LLM服务商和不同的模型。

## 二、项目预览

|WPS加载项界面|后端服务QT界面|
|--|--|
|![](./web/docs/public/wps_addon.png)|![](./web/docs/public/QtGUI.png)|

举个例子，以 WPS 的**单智能体（Single Agent）模式**为例：用户在加载项里输入“帮我把实习目的修改成 5 点”。智能体会按“**定位 → 读取 → 理解 → 编辑**”的流程完成任务：先调用 `search_document` 定位目标段落获取段落ID，再调用 `read_document` 根据段落ID读取对应段落内容；在分析理解后，调用 `delete_document` 删除原段落内容，最后调用 `generate_document` 生成新的修改结果。前端加载项会的WPS原生批注的方式显示修改后内容，便于用户直观看到变更。

![](./web/docs/public/generate_document_2x.gif)

另外，如果是小范围某一段落内的修改的，文策AI还提供 `edit_document` 工具，可以直接编辑修改目标段落ID的内容保持段落属性和段落ID不变，非常适合修改表格内容。

![](./web/docs/public/edit_document_2x.gif)

> 注意：生成结果不仅包含文字内容，还包含与之匹配的样式信息（如标题/正文、加粗、字体、缩进、行距等）。前端加载项会依据这些样式信息将内容渲染为符合 Word 文档结构与格式的最终效果。

除此之外，本项目还支持两类“可插拔扩展”来接入自定义工具：**MCP Server** 与 **Skill**。

1）**MCP Server 示例（第三方 API / 服务接入）**：用户可以通过配置 MCP 服务器，让智能体像调用内置工具一样调用第三方 API 来增强能力。以 **高德地图 MCP** 和 **可视化图表 MCP Server** 为例：当用户输入“查询长沙未来五天的天气，绘制一个气温折线统计图，并写一份天气预报文章”时，智能体会先调用高德地图 MCP 获取未来五天的气温数据，再调用可视化图表 MCP Server 生成折线图图片 URL，并将图片渲染在加载项界面中。

![](./web/docs/public/mcp_example.png)

2）**Skill 示例（能力打包与复用）**：Skill 更像是把一套可复用的能力与流程（例如提示词模板、工具调用编排、特定领域写作/处理逻辑等）封装成“技能包”。加载后，智能体可以根据任务需求选择并执行对应 Skill，用更稳定的路径完成特定类型任务。

![](./web/docs/public/skill-example.png)

## 三、开发计划

- [x] 支持单智能体模式
- [x] 支持MCP服务器和Skill工具接入
- [x] 支持上下文压缩
- [x] 支持长短期记忆
- [x] 支持表格、插图、公式等复杂样式编辑(公式可读但是不能生成)

#### 本项目支持的办公软件

- WPS Office Linux 版本 12.1.2.24722及以上、Windows 版本 12.1.0.28043 以下
- Microsoft Word（Windows、Web）版本 LTSC 2024及以上(wordAPI 1.6及以上)

## 四、系统架构

### 数据结构模型

不难看出，本项目的核心是稳定的**生成结构化文档**，文策AI定义的数据结构模型将内容与样式分离：`paragraphs`保存唯一的有序内容流，`styles`保存去重后的样式数组。内容节点通过`pS_N`、`rS_N`、`cS_N`、`tS_N`形式的ID引用样式，作用类似HTML元素引用CSS规则。

#### json schema示意图

![](./web/docs/public/json_schema.png)

### Agent loop架构

为了能够更好地满足用户需求，保证系统生成文章的稳定性和深度，本项目采用智能体循环架构：

#### 整体架构图

![](./web/docs/public/single_agent_loop.png)

前端设计的WPS加载项将用户的提问和当前用户选择的文章段落转化成特定json格式发送给后端。

在后端单智能体架构中，系统设计了一个标准的**ReAct**智能体循环架构，智能体在每个循环中根据用户输入和当前文档状态进行思考，选择调用哪种工具（如联网搜索工具）还是选择直接结束，选择调用了工具然后再思考，再选择调用哪种工具(如写作工具)或者选择结束，直到智能体选择结束循环。

- **read_document tool**: 负责读取(startParaIndex, endParaIndex)范围内的文章内容并转化成特定json格式回传给智能体。
- **generate_document tool**: 负责生成特定json格式的文章内容传给前端加载项。
- **search_document tool**: 负责查询某种格式或文字信息的段落位置并返回给智能体。
- **delete_document tool**: 负责根据段落ID删除相应内容。

## 五、快速开始

### 环境配置

- node v22.12.0
- wpsjs 2.2.3
- python 3.11.14
- Windows10/11、Ubuntu22.04、macOS

### 构建前端加载项

```bash
cd frontend/wps_word_plugin       # WPS Word加载项
cd frontend/microsoft_word_plugin # 或Microsoft Word加载项
pnpm install
pnpm build
```

### 运行后端服务

```bash
cd backend
uv run python main.py
```

### 使用Langsmith跟踪

另外，本项目还支持使用Langsmith进行智能体行为跟踪和分析，配置方法参考[后端README](backend/README.md)中的说明。

![](./web/docs/public/Langsmith.png)

### 项目软件打包

```bash
cd backend
uv run pyinstaller ../packaging/pyinstaller/package.spec --clean --noconfirm
```
通用应用目录会生成到 `backend/dist/wence_ai`。

Linux 使用 fpm 打包：

```bash
bash packaging/linux/build-deb.sh
```

Windows 使用 Inno Setup 打包：

```powershell
.\packaging\windows\build-installer.ps1
```

macOS 会打包为 `.app` 压缩包和 `.dmg` 安装包：

```bash
bash packaging/darwin/build-packages.sh
```

GitHub Actions 会生成平台安装包，并保留完整压缩包：

- `wence_ai-linux-x86_64.deb`
- `wence_ai-linux-x86_64-full.zip`
- `wence_ai-macos-arm64-app.zip`
- `wence_ai-macos-arm64.dmg`
- `wence_ai-windows-x86_64-installer.exe`
- `wence_ai-windows-x86_64-full.zip`

如果你不想自己打包，可以直接下载release中打包的压缩包，解压后点击exe文件即可使用。

### 软件下载

打包后的发行版文件详见[Release](https://github.com/visresearch/WordAgent/releases).

### 软件运行

下载后双击exe文件，启动后端服务（wence_word_plugin->安装），打开Word软件，信任加载项，即可体验服务。

## 六、LLM API适配情况

本项目对部分LLM API进行了测试，后续陆续测试适配中，具体情况如下：

- [x] Qwen 3.6 Plus运行稳定
- [x] GLM-5.1运行稳定
- [x] GPT 5.4运行稳定
- [x] MiniMax M2.5运行稳定
- [x] DeepSeek v4 pro运行稳定
- [x] Claude Sonnet/Opus 运行稳定
- [x] MiMo-V2.5 运行稳定

> 推荐使用 **GPT系列** 模型，效果最好，其次是 **Qwen系列** 模型，详情请看[测评文档](./backend/evaluation/README.md)

注：本项目开发使用了部分[阿里云百炼](https://bailian.console.aliyun.com/)、[Openrouter](https://openrouter.ai/models?q=free)免费额度

## 七、关于

与我交流：https://visresearch.github.io/WordAgent/guide/about.html

## 八、开源协议

本项目采用Apache License 2.0开源协议
