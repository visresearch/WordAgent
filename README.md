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
  English | <a href="README.zh-CN.md">中文文档</a>
</p>

> [!caution]
> If the WPS add-in freezes on recent Windows versions, switch the window management mode to multi-component mode in Settings. See [issue #1](https://github.com/visresearch/WordAgent/issues/1) for details.

## 1. Project Overview

This project is an AI-assisted writing system based on an agent workflow: **WenCe AI**. After installing the **add-in** in office software such as **WPS or Microsoft Word**, users can interact with the AI agent through natural language to get **writing suggestions**, **content generation**, **structure optimization**, and more.

> WenCe AI (Word Agent): strategy-driven writing, smarter expression

Compared with existing AI writing assistants on the market, WenCe AI provides:

1. **Multi-version and cross-platform support**: built on widely used office software with a Codex-style Word add-in, allowing general users to access high-quality AI writing assistance with a low barrier. It supports Windows, Linux, and macOS.
2. **Native rich text with document styles and paragraph editing**: compared with common AI writing tools in Word, this project allows agents to understand Word document structure, autonomously collect online information, generate content that fits Word document structure, and modify article structure and content according to user needs.
3. **Efficient editing with autonomous tool use**: the agent understands the task and document context, then selects suitable tools to complete writing and editing tasks.
4. **Open and flexible, with custom API or local service support**: the LLM API key used by this project is provided by the user. It currently supports most mainstream LLM providers, allowing users to choose different providers and models according to their needs.

## 2. Project Preview

| WPS Add-in UI | Backend QT UI |
| -- | -- |
| ![](./web/docs/public/wps_addon.png) | ![](./web/docs/public/QtGUI.png) |

For example, in WPS **Single Agent** mode, a user can enter: "Revise my internship objectives into five points." The agent completes the task through the "**locate -> read -> understand -> edit**" workflow: it first calls `search_document` to locate the target paragraph and obtain its paragraph ID, then calls `read_document` to read the paragraph content by ID. After analysis and understanding, it calls `delete_document` to remove the original paragraph, and finally calls `generate_document` to generate the revised result. The frontend add-in displays changes through WPS native tracked changes and revision balloons, making them easy to review.

![](./web/docs/public/generate_document_2x.gif)

For small changes within a single paragraph, WenCe AI also provides the `edit_document` tool. It edits the target paragraph by ID while preserving its paragraph properties and ID, making it especially useful for modifying table content.

![](./web/docs/public/edit_document_2x.gif)

> Note: the generated result includes not only text content, but also matching style information such as heading/body style, bold text, font, indentation, and line spacing. The frontend add-in renders the final result according to these styles so that it matches the Word document structure and format.

In addition, this project supports two types of pluggable extensions for custom tools: **MCP Server** and **Skill**.

1) **MCP Server example (third-party API/service integration)**: users can configure MCP servers so that agents can call third-party APIs like built-in tools. For example, with **Amap MCP** and a **visualization chart MCP Server**, when a user enters "Query Changsha's weather for the next five days, draw a temperature line chart, and write a weather forecast article," the agent first calls Amap MCP to obtain five-day temperature data, then calls the visualization chart MCP Server to generate a line-chart image URL and render the image in the add-in interface.

![](./web/docs/public/mcp_example.png)

2) **Skill example (capability packaging and reuse)**: Skill is like packaging a reusable capability and workflow, such as prompt templates, tool-call orchestration, or domain-specific writing/processing logic, into a "skill package." After loading, the agent can select and execute the corresponding Skill according to the task requirements, completing specific task types through a more stable path.

![](./web/docs/public/skill-example.png)

## 3. Development Plan

- [x] Single Agent mode
- [x] MCP server and Skill tool integration
- [x] Context compression
- [x] Short-term and long-term memory
- [x] Complex style editing for tables, illustrations, equations, etc. (equations are readable but cannot be generated)
- [ ] LAN access and cloud deployment beyond localhost

#### Supported Office Software

- WPS Office: Linux version 12.1.2.24722 or later; Windows versions below 12.1.0.28043
- Microsoft Word (Windows, Web), LTSC 2024 or later (WordApi 1.6 or later)

## 4. System Architecture

### Data Structure Model

The core of this project is the stable generation of **structured documents**. WenCe AI separates content and styles: `paragraphs` stores the only ordered content stream, while `styles` stores deduplicated style arrays. Content nodes reference styles through IDs such as `pS_N`, `rS_N`, `cS_N`, and `tS_N`, similar to HTML elements referencing CSS rules.

#### JSON Schema illustration

![](./web/docs/public/json_schema.png)

### Agent Loop Architecture

To better meet user needs and ensure the stability and depth of generated articles, this project uses an Agent loop architecture:

#### Overall Architecture Diagram

![](./web/docs/public/single_agent_loop.png)

The frontend WPS add-in converts the user's question and the currently selected document paragraphs into a specific JSON format and sends it to the backend.

In the backend Single Agent architecture, the system uses a standard ReAct agent loop. In each loop, the agent reasons based on the user input and current document state, decides whether to call a tool such as a web search tool or finish directly, then continues reasoning after tool calls and chooses another tool such as a writing tool or finishes, until the agent decides to end the loop.

- **read_document tool**: reads article content in the `(startParaIndex, endParaIndex)` range and converts it into a specific JSON format to return to the agent.
- **generate_document tool**: generates article content in a specific JSON format and sends it to the frontend add-in.
- **search_document tool**: searches paragraph positions by format or text information and returns them to the agent.
- **delete_document tool**: deletes corresponding content according to paragraph IDs.

## 5. Quick Start

### Environment Setup

- node v22.12.0
- wpsjs 2.2.3
- python 3.11.14
- Windows 10/11, Ubuntu 22.04, macOS

### Build Frontend Add-in

```bash
cd frontend/wps_word_plugin       # WPS Word add-in
cd frontend/microsoft_word_plugin # Or Microsoft Word add-in
pnpm install
pnpm build
```

### Run Backend Service

```bash
cd backend
uv run python main.py
```

### Use LangSmith Tracing

This project also supports LangSmith for tracing and analyzing agent behavior. For configuration, see the instructions in the [backend README](backend/README.md).

![](./web/docs/public/Langsmith.png)

### Package the Software

```bash
cd backend
uv run pyinstaller ../packaging/pyinstaller/package.spec --clean --noconfirm
```

The shared app directory is generated in `backend/dist/wence_ai`.

Linux releases are built with fpm:

```bash
bash packaging/linux/build-deb.sh
```

Windows releases are built with Inno Setup:

```powershell
.\packaging\windows\build-installer.ps1
```

macOS releases are built as an `.app` archive and a `.dmg` package:

```bash
bash packaging/darwin/build-packages.sh
```

GitHub Actions builds the platform packages and keeps the full archives:

- `wence_ai-linux-x86_64.deb`
- `wence_ai-linux-x86_64-full.zip`
- `wence_ai-macos-arm64-app.zip`
- `wence_ai-macos-arm64.dmg`
- `wence_ai-windows-x86_64-installer.exe`
- `wence_ai-windows-x86_64-full.zip`

If you do not want to package it yourself, you can directly download the packaged archive from the release, extract it, and run the executable.

### Software Download

Packaged release files are available in [Release](https://github.com/visresearch/WordAgent/releases).

### Run the Software

After downloading, double-click the executable to start the backend service (`wence_word_plugin -> Install`), open Word, trust the add-in, and start using the service.

## 6. LLM API Compatibility

This project has tested some LLM APIs and will continue testing and adapting more APIs. Current status:

- [x] Qwen 3.6 Plus runs stably
- [x] GLM-5.1 runs stably
- [x] GPT 5.4 runs stably
- [x] MiniMax M2.5 runs stably
- [x] DeepSeek v4 pro runs stably
- [x] Claude Sonnet/Opus runs stably
- [x] MiMo-V2.5 runs stably

> GPT series models are recommended for the best results, followed by Qwen series models. See the [evaluation document](./backend/evaluation/README.md) for details.

Note: this project used some free quotas from [Alibaba Cloud Bailian](https://bailian.console.aliyun.com/) and [OpenRouter](https://openrouter.ai/models?q=free) during development.

## 7. About

Contact: https://visresearch.github.io/WordAgent/guide/about.html

## 8. License

Apache License 2.0.
