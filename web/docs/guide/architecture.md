# 系统架构

## 整体设计

本项目采用 FastAPI 构建后端 API，前端 WPS/Word 加载项通过 WebSocket 与后端通信，使前端能够流式显示 LLM 输出、工具调用状态和错误信息。

- **前端**：Vue3 + JavaScript 开发，包含 DocxJson 双向转化器模块，能够将带格式的 Word 文档内容与 JSON 格式进行相互转换
- **后端**：使用 Python、LangChain 和 LangGraph 实现智能体编排，通过 OpenAI/Anthropic 兼容接口完成流式输出与工具调用，并由 PySide6 提供桌面服务界面
- **外部 Agent 接口**：通过 Streamable HTTP 文档 MCP Server 将 WPS / Microsoft Word 工具提供给 Codex 等客户端，工具请求经加载项的 WebSocket 桥接在目标文档执行

## 文档数据结构

生成结构化 Word 文档是本项目的核心。后端的 `DocumentOutput` 模型将内容与样式分离：`paragraphs` 保存唯一的有序内容流，`styles` 保存去重后的样式数组。内容节点通过 `pS_N`、`rS_N`、`cS_N`、`tS_N` 形式的 ID 引用样式，作用类似 HTML 元素引用 CSS 规则。

![](/json_schema.png)

`styles` 中的每个值都是由字符串、数字或布尔值组成的数组，不能包含 `null`。所有被内容节点引用的样式 ID 都必须存在。

| 样式 ID | 最少项数 | 数组顺序 | 含义 |
|---|---|---|---|
| `pS_N` | 9 | [alignment, lineSpacing, indentLeft, indentRight, indentFirstLine, spaceBefore, spaceAfter, styleName, lineSpacingRule] | [对齐方式, 行间距, 左缩进, 右缩进, 首行缩进, 段前间距, 段后间距, 样式名称, 行间距规则] |
| `rS_N` | 11 | [fontName, fontSize, bold, italic, underline, underlineColor, color, highlight, strikethrough, superscript, subscript] | [字体名, 字号, 粗体, 斜体, 下划线, 下划线颜色, 颜色, 高亮, 删除线, 上标, 下标] |
| `cS_N` | 4 | [rowSpan, colSpan, alignment, verticalAlignment] | [行跨度, 列跨度, 水平对齐方式, 垂直对齐方式] |
| `tS_N` | 1 | [tableAlignment] | [表格对齐方式] |

其中，段落对齐方式为 `left`、`center`、`right` 或 `justify`；颜色使用 `#RRGGBB`。下划线常用值包括 `0`（无）、`1`（单线）、`3`（双线）、`4`（虚线）、`6`（粗线）和 `11`（波浪线）。表格对齐值为 `0`（左）、`1`（中）、`2`（右）；行高规则为 `0`（自动）、`1`（至少）或 `2`（固定）。

## Agent Loop 架构

Agent 与 Ask 使用 ReAct 循环。Agent 可以读取并修改文档；Ask 只保留读取、搜索与分析能力，不会生成或删除 Word 内容。

![单智能体架构](/single_agent_loop.png)

工具列表：

- **read_document / search_document**：读取文档并定位内容
- **generate_document / edit_document / delete_document**：新增内容、原位改写段落或删除段落（Ask 不可用；`edit_document` 保留目标段落的 `pStyle`）
- **create_document / insert_break**：创建空白文档，或插入换行、分页和分节符
- **load_skill_context**：按任务加载已启用 Skill
- **list_file / read_file / edit_file**：处理任务文件
- **python_repl**：执行数据处理（Agent 模式）
- **MCP 工具**：调用用户配置的搜索、图表和其他外部服务

当前仅提供 Agent 和 Ask 两种模式。需要改写单个段落时，使用 `edit_document(paraID, runs)` 直接替换正文并保留原段落样式；Ask 模式不会生成或删除 Word 内容。

## 模型参数与文档 MCP

内置 Agent / Ask 对话按“提供商 + 模型”读取已保存的生成参数：Temperature、Top-p、Max Tokens 和 Reasoning Effort。模型参数持久化到本机数据库，前端编辑入口见 [模型参数面板](/guide/api-config#编辑-llm-模型参数)。

MCP 有两条调用路径：

| 路径 | 配置入口 | 用途 |
|---|---|---|
| 文策 AI → 第三方 MCP | 加载项 **设置 → MCP** | 为内置智能体添加搜索、图表等工具 |
| 外部 Agent → 文策 AI 文档 MCP | 桌面程序 **MCP 服务器** | 让 Codex 等客户端调用当前 WPS / Microsoft Word 文档工具 |

外部文档 MCP 的默认地址为 `http://127.0.0.1:3880/mcp/`，调用时需打开目标文档的加载项侧栏。外部 Agent 使用其客户端的模型和推理配置，文策 AI 的模型参数用于内置对话。连接方式见 [文档 MCP Server](/guide/mcp-server)。

## Langsmith 集成

本项目支持使用 Langsmith 进行智能体行为跟踪和分析，方便调试和优化智能体性能。

![Langsmith](/Langsmith.png)

## 前后端接口预览

![](/api.jpg)

表格尺寸使用平行的一维数组：`rowHeights: [25, 30]` 表示从上到下的行高（磅），`rowHeightRules: [1, 2]` 表示最小高度和固定高度（`0` 为自动）。读取时的 `paraID` / `endParaID` 是表格首末段落的定位锚点；`pageStart` / `pageEnd` 是可用时的原生物理页码。删除表格统一通过 `delete_document(startParaID, endParaID)` 覆盖完整表格范围，不使用独立表格 ID 或逐单元格清空。
