# Word Agent

![](./web/docs/public/WenceAI_small.png)

<p align="center">
  <a href="backend/pyproject.toml"><img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white" alt="Python" /></a>
  <a href="backend/README.md"><img src="https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white" alt="FastAPI" /></a>
  <a href="https://www.langchain.com/"><img src="https://img.shields.io/badge/LangChain-Used-1C3C3C?logo=chainlink&logoColor=white" alt="LangChain" /></a>
  <a href="https://www.langchain.com/langgraph"><img src="https://img.shields.io/badge/LangGraph-Multi--Agent-0B3D91" alt="LangGraph" /></a>
  <a href="frontend/microsoft_word_plugin/package.json"><img src="https://img.shields.io/badge/Node.js-v22%2B-339933?logo=node.js&logoColor=white" alt="Node.js" /></a>
  <a href="README.md"><img src="https://img.shields.io/badge/Version-v1.0.0-orange.svg" alt="Version" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg" alt="License" /></a>
</p>

<p align="center">
  <a href="README.md">English</a> | <a href="README.zh-CN.md">中文文档</a>
</p>

## 1. Overview

This project is an AI-assisted writing system based on (multi-)agent workflows: **WenCe AI (Word Agent)**. After users install the add-in in office suites (such as WPS and Microsoft Word), they can interact with AI through natural language to get **writing suggestions**, **content generation**, and **structure optimization**.

> WenCe AI (Word Agent): strategy-driven writing, smarter expression.

The backend is built with FastAPI. The frontend WPS add-in communicates with the backend via streaming APIs, so users can see LLM outputs in real time for a smooth writing-assistant experience.

The frontend uses Vue 3 and JavaScript. A key module is the DocxJson bidirectional converter, which converts formatted Word content and JSON structures back and forth.

The backend is implemented in Python, using LangChain and LangGraph for agent design and collaboration, ChatOpenAI-compatible APIs for SSE streaming and tool calling, and a lightweight PySide6 desktop panel for add-in installation and terminal log inspection.

At its core, this project focuses on **structured Word document generation**. The project defines a JSON schema conceptually similar to HTML and CSS, abstracting paragraph and text-run style attributes so the agent can better understand and generate well-formatted Word content.

Main JSON data structures:

- **paragraphs**: an array of Word paragraphs containing multiple runs; this is the primary editable object for the agent
  - **pStyle**: paragraph style ID (for example, Heading 1, Heading 2, Body)
  - **runs**: text-run array, the smallest content unit in this project
    - **text**: text content
    - **rStyle**: character style ID (for example, bold, red)
  - **paraIndex**: paragraph index, used by the agent to locate and edit a specific paragraph precisely
- **styles**: style-definition dictionary that contains all paragraph and character style definitions; the agent references these style IDs to preserve formatting correctness

Compared with many AI writing assistants on the market, WenCe AI provides:

1. **Cross-version and cross-platform support**: built on mainstream office software with a Copilot-like Word add-in UX, lowering the barrier for general users, and supporting both Windows and Linux.
2. **Native rich-text editing with style and paragraph awareness**: unlike many Word AI tools, this project can understand Word document structure, autonomously gather online information, and modify both structure and content based on user requirements.
3. **Efficient editing with multi-agent collaboration**: multiple agents take different **expert roles** and collaborate to produce in-depth long-form writing.
4. **Open and flexible integration**: supports user-provided API keys and is compatible with most mainstream LLM providers and models.

## 2. Project Preview

| WPS Add-in UI | Backend Qt UI |
| -- | -- |
| ![](./web/docs/public/wps_addon.png) | ![](./web/docs/public/pyQt.png) |

For example, in WPS single-agent mode, if the user asks: "Expand my internship objective into five points," the agent first calls `search_document` to locate the paragraph, then calls `read_document` to fetch the content, analyzes it, calls `delete_document` to remove the original text, and finally calls `generate_document` to produce the rewritten result. The frontend add-in renders before/after changes with different highlight colors, so users can clearly see what was modified.

![](./web/docs/public/preview2.png)

The generated article conforms to Word document structure and formatting. While generating text, the agent also returns style metadata (such as titles, body text, bold, font, indentation, and line spacing). The frontend add-in then renders content into properly formatted Word output based on these style definitions.

In addition, this project supports custom tool integration. Users can configure MCP servers to let the agent call third-party APIs and extend capabilities. Taking **Amap Maps MCP** and **Visualization Chart MCP Server** as examples: when a user asks, "Query Changsha's weather for the next five days, draw a temperature line chart, and write a weather report," the agent can call the Amap MCP server to retrieve temperature data, then call the chart MCP server to generate an image URL and render it in the add-in chat panel.

![](./web/docs/public/mcp_example.png)

## 3. Development Plan

- [x] Single-agent mode
- [x] Multi-agent mode
- [x] Remote MCP server integration
- [ ] Local MCP server and Skill tool integration
- [ ] Advanced style editing (tables, illustrations, equations, etc.)

#### Supported Office Suites

- WPS Office (Windows, Linux), version 12.1.25225 and above
- Microsoft Word (Windows, Web), version 2019/2021 and above

## 4. System Architecture

To better satisfy user needs and improve generation stability and depth, the project provides two agent architectures.

### 4.1 Single-Agent Loop Architecture

#### Architecture Diagram

![](./web/docs/public/single_agent_loop.png)

The frontend WPS add-in converts the user's request and selected document range into structured JSON and sends it to the backend.

In the backend single-agent architecture, the system follows a standard ReAct loop. In each round, the agent reasons over user input and current document state, chooses whether to call a tool (such as web search) or finish directly, and continues this tool-use/reasoning loop until completion.

- **read_document tool**: reads content in the `(startPosition, endPosition)` range and returns structured JSON to the agent.
- **generate_document tool**: generates structured JSON document content and returns it to the frontend add-in.
- **search_document tool**: locates paragraph positions by format or text criteria and returns positions to the agent.
- **web_fetch tool**: fetches information from user-provided links.

### 4.2 Multi-Agent Architecture

#### Architecture Diagram

![](./web/docs/public/multi_agent.png)

The frontend flow is the same as in single-agent mode. In the backend multi-agent workflow, a **planner agent** orchestrates and schedules several specialized agents.

- **research agent**: collects online reference information
- **outline agent**: generates an outline based on references and user requirements
- **writer agent**: writes content based on references and user requirements
- **reviewer agent**: reviews generated content and provides revision suggestions

## 5. Quick Start

### Environment Setup

- Node v22.12.0
- wpsjs 2.2.3
- Python 3.11.14
- Windows 10/11 or Ubuntu 22.04

### Build Frontend Add-in

```bash
# Option A: WPS Word add-in
cd frontend/wps_word_plugin

# Option B: Microsoft Word add-in
# cd frontend/microsoft_word_plugin

pnpm install
pnpm build
```

### Run Backend Service

```bash
cd backend
uv run python main.py
```

### Use LangSmith Tracing

The project also supports LangSmith for tracing and analyzing agent behavior. For setup details, see [backend/README.md](backend/README.md).

![](./web/docs/public/Langsmith.png)

### Package the Desktop App

```bash
cd backend/deploy
uv run pyinstaller wence.spec
```

The packaged executable is generated in `backend/deploy/dist`.

If you do not want to package it yourself, you can directly download the packaged archive from Releases and run the executable after extraction.

### Download

Packaged release files: [Release](https://github.com/visresearch/WordAgent/releases).

### Run the App

After downloading, run the executable, start the backend service (`wence_word_plugin -> Install`), open Word, trust the add-in, and start using the system.

You need to configure an LLM API. This project is currently tested with Alibaba Bailian Qwen3.5-Plus APIs.

## 6. LLM API Compatibility

The project has tested part of the mainstream LLM APIs in China, and compatibility is still expanding:

- [x] Qwen 3.5 Plus (stable)
- [x] Qwen3 Max (stable)
- [x] GLM-5 (stable)
- [x] GPT 5.4 (stable)
- [x] MiniMax M2.5 (stable)
- [x] Step 3.5 Flash (stable)
- [x] DeepSeek v3.2 (stable)
- [x] Claude Sonnet 4.6 (issues with document-generation tool calls)
- [x] Kimi K2.5 (can fall into tool-call loops)
- [ ] Gemini 3.1 Pro

Note: part of development used free quotas from [Alibaba Bailian](https://bailian.console.aliyun.com/) and [OpenRouter](https://openrouter.ai/models?q=free).

## 7. About the Author

Contact: https://cmcblog.netlify.app/about/

## 8. License

Apache License 2.0.
