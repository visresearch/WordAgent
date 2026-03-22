# 系统架构

## 整体设计

本项目采用 FastAPI 构建后端 API，前端 WPS/Word 加载项与后端利用流式接口通信，实现无缝的写作辅助体验。

- **前端**：Vue3 + JavaScript 开发，包含 DocxJson 双向转化器模块，能够将带格式的 Word 文档内容与 JSON 格式进行相互转换
- **后端**：Python 语言，利用 LangChain 和 LangGraph 框架实现智能体的设计和协作，利用 PySide6 设计后端服务界面

## 文档数据结构

生成结构化 Word 文档是本项目的核心。项目中定义的 JSON Schema 格式类似于 Web 开发中的 HTML 和 CSS，将 Word 文章的段落和文本块的样式属性都进行了抽象和结构化：

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

- **read_document**：读取指定范围内的文章内容并转化成 JSON 格式
- **generate_document**：生成 JSON 格式的文章内容传给前端加载项
- **query_document**：查询某种格式或文字信息的段落位置
- **web_search**：根据关键词联网搜索并返回结果

## Multi Agent 架构

多智能体协作框架中设计了一个 **Planner Agent** 负责编排和调度其他专家智能体的工作流。

![多智能体架构](/multi_agent.png)

| 智能体 | 职责 |
|---|---|
| **Planner Agent** | 编排和调度其他智能体 |
| **Research Agent** | 联网搜集资料信息 |
| **Outline Agent** | 根据资料和需求生成文章大纲 |
| **Writer Agent** | 根据资料和需求生成文章内容 |
| **Reviewer Agent** | 对生成的文章进行审阅和修改建议 |
