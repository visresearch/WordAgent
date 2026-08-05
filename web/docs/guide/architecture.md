# 系统架构

## 整体设计

本项目采用 FastAPI 构建后端 API，前端 WPS/Word 加载项通过 WebSocket 与后端通信，使前端能够流式显示 LLM 输出、工具调用状态和错误信息。

- **前端**：Vue3 + JavaScript 开发，包含 DocxJson 双向转化器模块，能够将带格式的 Word 文档内容与 JSON 格式进行相互转换
- **后端**：使用 Python、LangChain 和 LangGraph 实现智能体编排，通过 OpenAI/Anthropic 兼容接口完成流式输出与工具调用，并由 PySide6 提供桌面服务界面

## 文档数据结构

生成结构化 Word 文档是本项目的核心。后端的 `DocumentOutput` 模型将内容与样式分离：`paragraphs` 保存唯一的有序内容流，`styles` 保存去重后的样式数组。内容节点通过 `pS_N`、`rS_N`、`cS_N`、`tS_N` 形式的 ID 引用样式，作用类似 HTML 元素引用 CSS 规则。

![](/jsonschema.png)

`styles` 中的每个值都是由字符串、数字或布尔值组成的数组，不能包含 `null`。所有被内容节点引用的样式 ID 都必须存在。

| 样式 ID | 最少项数 | 数组顺序 | 含义 |
|---|---|---|---|
| `pS_N` | 9 | [alignment, lineSpacing, indentLeft, indentRight, indentFirstLine, spaceBefore, spaceAfter, styleName, lineSpacingRule] | [对齐方式, 行间距, 左缩进, 右缩进, 首行缩进, 段前间距, 段后间距, 样式名称, 行间距规则] |
| `rS_N` | 11 | [fontName, fontSize, bold, italic, underline, underlineColor, color, highlight, strikethrough, superscript, subscript] | [字体名, 字号, 粗体, 斜体, 下划线, 下划线颜色, 颜色, 高亮, 删除线, 上标, 下标] |
| `cS_N` | 4 | [rowSpan, colSpan, alignment, verticalAlignment] | [行跨度, 列跨度, 水平对齐方式, 垂直对齐方式] |
| `tS_N` | 1 | [tableAlignment] | [表格对齐方式] |

其中，段落对齐方式为 `left`、`center`、`right` 或 `justify`；颜色使用 `#RRGGBB`。下划线常用值包括 `0`（无）、`1`（单线）、`3`（双线）、`4`（虚线）、`6`（粗线）和 `11`（波浪线）。表格对齐值为 `0`（左）、`1`（中）、`2`（右）；行高规则为 `0`（自动）、`1`（至少）或 `2`（固定）。

## Agent / Ask 架构

Agent 与 Ask 使用 ReAct 循环。Agent 可以读取并修改文档；Ask 只保留读取、搜索与分析能力，不会生成或删除 Word 内容。

![单智能体架构](/single_agent_loop.png)

工具列表：

- **read_document / search_document**：读取文档并定位内容
- **generate_document / edit_document / delete_document**：新增内容、原位改写段落或删除段落（Ask 不可用；`edit_document` 保留目标段落的 `pStyle`）
- **create_document / insert_break**：创建空白文档，或插入换行、分页和分节符
- **load_skill_context**：按任务加载已启用 Skill
- **list_file / read_file / edit_file**：处理任务文件
- **python_repl**：执行数据处理（Agent 模式）
- **review_document / create_workflow**：Plan 模式中的审阅和工作流编排工具
- **MCP 工具**：调用用户配置的搜索、图表和其他外部服务

单智能体 Agent 模式当前暂时停用 `run_sub_agent` 工具，不会自动委派子任务；需要改写单个段落时，使用 `edit_document(paraID, runs)` 直接替换正文并保留原段落样式。

## Plan（Multi-Agent）架构 (实验功能，在0.6.0版本后移除)

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

## 前后端接口预览

![](/api.jpg)
