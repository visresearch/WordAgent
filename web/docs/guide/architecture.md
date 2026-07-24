# 系统架构

## 整体设计

本项目采用 FastAPI 构建后端 API，前端 WPS/Word 加载项通过 WebSocket 与后端通信，使前端能够流式显示 LLM 输出、工具调用状态和错误信息。

- **前端**：Vue3 + JavaScript 开发，包含 DocxJson 双向转化器模块，能够将带格式的 Word 文档内容与 JSON 格式进行相互转换
- **后端**：使用 Python、LangChain 和 LangGraph 实现智能体编排，通过 OpenAI/Anthropic 兼容接口完成流式输出与工具调用，并由 PySide6 提供桌面服务界面

## 文档数据结构

生成结构化 Word 文档是本项目的核心。项目中定义的 JSON Schema 格式类似于 Web 开发中的 HTML 和 CSS，将 Word 文章的段落和文本块的样式属性都进行了抽象和结构化，方便智能体理解和生成。

- **paragraphs**: word文档段落数组，包含多个run文本块，paragraphs是agent主要修改的对象
  - **pStyle**: 段落样式ID（如标题1、标题2、正文等）
  - **runs**: 文本块数组，本项目中定义的文档的最小单位
    - **text**: 文本内容
    - **rStyle**: 字符样式ID（如加粗、红色等）
  - **paraIndex**: 段落索引，智能体可以根据这个索引定位到文档中的具体段落进行读取
  - **paraID**: 段落唯一标识，智能体可以根据这个标识定位到文档中的具体段落进行修改
- **styles**: 样式定义字典，包含所有段落样式和字符样式的定义，智能体生成文档时需要引用这些样式ID来保证文档格式正确

## Agent / Ask 架构

Agent 与 Ask 使用 ReAct 循环。Agent 可以读取并修改文档；Ask 只保留读取、搜索与分析能力，不会生成或删除 Word 内容。

![单智能体架构](/single_agent_loop.png)

工具列表：

- **read_document / search_document**：读取文档并定位内容
- **generate_document / delete_document**：生成或删除 Word 内容（Ask 不可用）
- **load_skill_context**：按任务加载已启用 Skill
- **list_file / read_file / edit_file**：处理任务文件
- **python_repl / run_sub_agent**：执行数据处理或委派子任务（Agent 模式）
- **MCP 工具**：调用用户配置的搜索、图表和其他外部服务

## Plan（Multi-Agent）架构

多智能体协作框架中设计了一个 **Planner Agent** 负责编排和调度其他专家智能体的工作流。

![多智能体架构](/multi_agent.png)

| 智能体 | 职责 |
|--------|------|
| **Planner Agent** | 编排和调度其他智能体的工作流 |
| **Research Agent** | 联网搜集资料信息 |
| **Outline Agent** | 根据资料信息和用户需求生成文章大纲 |
| **Writer Agent** | 根据资料信息和用户需求生成文章内容 |
| **Reviewer Agent** | 根据资料信息和用户需求对生成的文章进行审阅和修改建议 |

### 多智能体模式工作流程

以 **Plan 模式**为例，当用户请求写一篇长篇小说并绘制插图时，各专家智能体会依次工作：

1. **Planner Agent**：编排智能体流程
2. **Research Agent**：搜索网文小说，调用文生图
3. **Outline Agent**：描述小说大纲
4. **Writer Agent**：输出文章内容
5. **Reviewer Agent**：回顾文章段落，提出修改意见

### 多智能体模式特点

- **优势**：更容易生成长文，能够不跑题以及首尾呼应
- **局限**：工具调用能力略差于单智能体

### 典型工作流模式

| 模式 | 适用场景 | 流程 |
|------|----------|------|
| **纯创作** | 写一篇新文章 | research → outline → writer → reviewer（可选） |
| **文档修改** | 润色、翻译、扩写 | writer：直接修改文档 |
| **深度调研** | 需要联网搜索 | research → outline → writer → reviewer（可选） |
| **定向写作** | 基于现有文档写特定章节 | outline：读取文档，定位章节 → writer：写目标内容 |

## Langsmith 集成

本项目支持使用 Langsmith 进行智能体行为跟踪和分析，方便调试和优化智能体性能。

![Langsmith](/Langsmith.png)

## MCP 服务器支持

本项目支持用户自定义工具的接入，通过配置 MCP 服务器的方式让智能体调用第三方 API 来增强智能体的能力。

支持的 MCP 服务器类型：

- **远程 MCP 服务器**：如高德地图等在线服务
- **本地 MCP 服务器**：本地部署的工具服务
- **Skill 工具**：自定义技能工具

示例：以**高德地图**和**可视化图表-MCP-Server**为例，用户输入"查询长沙未来五天的天气，绘制一个气温折线统计图，写一份天气预报文章"。智能体会调用高德地图 MCP 服务器进行查询长沙最近几天的气温数据，然后智能体会调用可视化图表-MCP-Server 生成一个折线统计图的图片 URL，把这张图片渲染在前端加载项界面中。
