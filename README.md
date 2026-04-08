# Word Agent

![](./docs/WenceAI_small.png)

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

Word Agent is an AI-assisted writing system (single-agent and multi-agent): WenCe AI. After installing the add-in in office suites (such as WPS and Microsoft Word), users can interact with AI through natural language to get writing suggestions, content generation, and structure optimization.

> WenCe AI (Word Agent): strategy-driven writing, smarter expression.

The backend is built with FastAPI. The frontend add-ins communicate with the backend through streaming interfaces so users can see LLM outputs in real time and get a seamless writing-assistant experience.

The frontend is built with Vue 3 and JavaScript. A key module is the DocxJson bidirectional converter, which transforms formatted Word content to JSON and back.

The backend is built with Python and uses LangChain + LangGraph for agent design and orchestration. ChatOpenAI-compatible APIs are used for streaming and tool calling. A lightweight PySide6 GUI is also provided for add-in installation and log monitoring.

The core of this project is **structured Word document generation**. The project defines a JSON schema (conceptually similar to HTML + CSS) to model Word paragraphs and text run styles so agents can understand and generate formatted documents reliably.

Main data structures:

- **paragraphs**: an array of Word paragraphs (the main editable unit)
  - **pStyle**: paragraph style ID (for example, Heading 1, Heading 2, Body)
  - **runs**: text run array (smallest text unit in this project)
    - **text**: run text
    - **rStyle**: character style ID (for example, bold, red)
  - **paraIndex**: paragraph index used by agents for precise location and editing
- **styles**: a style dictionary containing all paragraph/character style definitions referenced by style IDs

Compared with common AI writing tools, WenCe AI focuses on:

1. **Cross-version and cross-platform compatibility**: built on mainstream office software with a Copilot-like add-in experience, available on Windows and Linux.
2. **Native rich-text document editing**: agents understand Word structure, can search the web, and can modify both structure and content with formatting awareness.
3. **Efficient editing with multi-agent collaboration**: specialized agents cooperate to produce deeper long-form content.
4. **Open model ecosystem**: users can configure their own API providers and models.

## 2. Preview

| WPS Add-in UI | Backend Qt UI |
| -- | -- |
| ![](./docs/wps_addon.png) | ![](./docs/pyQt.png) |

Example (single-agent mode): in WPS, a user asks for a detailed report on the Iran war. The agent can call `web_search` to gather references and then call `generate_document` to produce Word-structured content for rendering in the add-in.

![](./docs/preview.png)

Generated content includes both text and formatting metadata (title/body styles, bold, fonts, indentation, spacing, etc.), which allows rendering as a properly formatted Word document.

Another example: when a user asks, "Expand my internship objective into five points," the agent can first call `query_document` to locate target paragraphs, then call `read_document` to fetch the original content, call `delete_document` to remove old text, and finally call `generate_document` to produce the rewritten result.

The frontend add-in can render before/after changes with different highlight colors so users can clearly see what was modified.

![](./docs/preview2.png)

## 3. Roadmap

- [x] WPS Word desktop support
- [x] Windows and Linux support
- [x] Single-agent mode
- [ ] Multi-agent mode
- [x] Microsoft Word web and desktop support
- [ ] Advanced styles (tables, figures, etc.)

## 4. Architecture

The project provides two agent architectures for different task complexity.

### 4.1 Single-agent loop

![](./docs/single_agent_loop.png)

The frontend sends user prompts and selected document ranges to the backend.

The backend runs a ReAct-style loop. In each loop, the agent decides whether to call a tool or finish. After tool results return, the agent reasons again and continues until completion.

Core tools:

- **read_document**: reads a paragraph range and returns structured JSON.
- **generate_document**: generates structured document JSON for frontend rendering.
- **query_document**: locates paragraphs by content/style criteria.
- **web_search**: retrieves online references for grounded writing.

### 4.2 Multi-agent workflow

![](./docs/multi_agent.png)

The frontend flow is the same, while the backend uses a planner-driven multi-agent workflow.

- **planner agent**: decomposes and schedules workflow steps
- **research agent**: gathers external references
- **outline agent**: creates document outline
- **writer agent**: generates document content
- **reviewer agent**: reviews quality and provides rewrite feedback

## 5. Quick Start

### 5.1 Environment

- Node v22.12.0
- wpsjs 2.2.3
- Python 3.11.14
- Windows 10/11 or Ubuntu 22.04

### 5.2 Build frontend add-in

```bash
# Option A: WPS Word add-in
cd frontend/wps_word_plugin
# Option B: Microsoft Word add-in
# cd frontend/microsoft_word_plugin
pnpm install
pnpm build
```

### 5.3 Run backend service

```bash
cd backend
uv run python main.py
```

### 5.4 LangSmith tracing

The project supports LangSmith tracing for agent behavior analysis. See [backend/README.md](backend/README.md) for setup details.

![](./docs/Langsmith.png)

### 5.5 Packaging

```bash
cd backend/deploy
uv run pyinstaller wence.spec
```

Built binaries are located in `backend/deploy/dist`.

You can also download packaged artifacts from Releases.

### 5.6 Download

Release artifacts: [Release](https://github.com/visresearch/WordAgent/releases)

### 5.7 Run packaged app

After download, extract the package and run the executable. Start backend service (`wence_word_plugin` -> install), open Word, trust the add-in, and start using the system.

You must configure an LLM API provider. The project has been tested with Alibaba Bailian Qwen models.

## 6. LLM API Status

Current compatibility status (ongoing):

- [x] Qwen 3.5 Plus (stable)
- [x] Qwen3 Max (stable)
- [x] GLM-5 (stable)
- [x] GPT 5.4 (stable)
- [x] MiniMax M2.5 (stable)
- [x] Step 3.5 Flash (stable)
- [x] DeepSeek v3.2 (stable)
- [x] Claude Sonnet 4.6 (issues when calling document-generation tools)
- [x] Kimi K2.5 (may enter tool-call loops)
- [ ] Gemini 3.1 Pro

Note: part of development used free credits from [Alibaba Bailian](https://bailian.console.aliyun.com/) and [OpenRouter](https://openrouter.ai/models?q=free).

## 7. Author

Contact: https://cmcblog.netlify.app/about/

## 8. License

Apache License 2.0
