# 系统架构

## 整体设计

本项目采用 FastAPI 构建后端 API，前端 WPS/Word 加载项与后端利用流式 SSE 接口通信，使前端流式显示 LLM 输出的内容，实现无缝的写作辅助体验。

- **前端**：Vue3 + JavaScript 开发，包含 DocxJson 双向转化器模块，能够将带格式的 Word 文档内容与 JSON 格式进行相互转换
- **后端**：Python 语言，利用 LangChain 和 LangGraph 框架实现智能体的设计和协作，用 ChatOpenAI 接口实现 SSE 流式输出和工具调用，利用 PySide6 设计了一个简单的后端服务界面，方便安装加载项和查看终端日志

## 文档数据结构

生成结构化 Word 文档是本项目的核心。项目中定义的 JSON Schema 格式类似于 Web 开发中的 HTML 和 CSS，将 Word 文章的段落和文本块的样式属性都进行了抽象和结构化，方便智能体理解和生成。

```
paragraphs (段落数组)
├── pStyle       段落样式ID（如标题1、标题2、正文等）
├── paraIndex    段落索引，用于定位具体段落
└── runs (文本块数组)
    ├── text     文本内容
    └── rStyle   字符样式ID（如加粗、红色等）

styles (样式定义字典)
├── 段落样式定义
└── 字符样式定义
```

## Single Agent Loop 架构

标准的 ReAct 智能体循环架构，智能体在每个循环中根据用户输入和当前文档状态进行思考，选择调用工具或结束任务。

![单智能体架构](/single_agent_loop.png)

工具列表：

- **read_document**：读取 (startPosition, endPosition) 范围内的文章内容并转化成 JSON 格式回传给智能体
- **generate_document**：生成 JSON 格式的文章内容传给前端加载项
- **search_document**：查询某种格式或文字信息的段落位置并返回给智能体
- **web_fetch**：根据用户输入的网站链接进行抓取获取信息

## Multi Agent 架构

多智能体协作框架中设计了一个 **Planner Agent** 负责编排和调度其他专家智能体的工作流。

![多智能体架构](/multi_agent.png)

| 智能体 | 职责 |
|--------|------|
| **Planner Agent** | 编排和调度其他智能体的工作流 |
| **Research Agent** | 联网搜集资料信息 |
| **Outline Agent** | 根据资料信息和用户需求生成文章大纲 |
| **Writer Agent** | 根据资料信息和用户需求生成文章内容 |
| **Reviewer Agent** | 根据资料信息和用户需求对生成的文章进行审阅和修改建议 |

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
