"""
文档处理 Agent - 使用 LangGraph + 流式输出
"""

import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.config import get_stream_writer
from langgraph.graph import END, START, MessagesState, StateGraph
from pydantic import BaseModel, Field

from app.services.llm_client import LLMClientManager, resolve_model

# # ============== Query DSL 模型定义 ==============

# """
# Query DSL 设计说明：
# 类似 Elasticsearch 的查询语法，支持多种查询类型和布尔组合

# 示例：
# 1. 关键词搜索：{"match": {"field": "text", "query": "公司名称"}}
# 2. 标题搜索：{"match": {"field": "styleName", "query": "标题"}}
# 3. 位置搜索：{"range": {"field": "index", "gte": 0, "lte": 5}}
# 4. 布尔组合：{"bool": {"must": [...], "should": [...], "must_not": [...]}}
# 5. 全文：{"match_all": {}}
# """


# class MatchQuery(BaseModel):
#     """匹配查询 - 搜索包含指定内容的段落"""

#     field: Literal["text", "styleName", "fontName"] = Field(
#         default="text", description="搜索字段: text=段落文本, styleName=样式名(如'标题1'), fontName=字体名"
#     )
#     query: str = Field(description="搜索关键词")
#     fuzzy: bool = Field(default=False, description="是否模糊匹配")


# class RangeQuery(BaseModel):
#     """范围查询 - 按位置范围搜索"""

#     field: Literal["index", "position"] = Field(
#         default="index", description="范围字段: index=段落索引(从0开始), position=字符位置"
#     )
#     gte: int | None = Field(default=None, description="大于等于")
#     lte: int | None = Field(default=None, description="小于等于")
#     gt: int | None = Field(default=None, description="大于")
#     lt: int | None = Field(default=None, description="小于")


# class TermQuery(BaseModel):
#     """精确匹配 - 用于布尔值或精确值"""

#     field: Literal["isEmpty", "isHeading", "isBold", "hasHighlight"] = Field(description="精确匹配字段")
#     value: bool | int | str = Field(description="匹配值")


# class QueryClause(BaseModel):
#     """单个查询子句"""

#     match: MatchQuery | None = Field(default=None, description="匹配查询")
#     range: RangeQuery | None = Field(default=None, description="范围查询")
#     term: TermQuery | None = Field(default=None, description="精确匹配")
#     match_all: dict | None = Field(default=None, description="匹配全部，使用空字典 {}")


# class BoolQuery(BaseModel):
#     """布尔查询 - 组合多个条件"""

#     must: list[QueryClause] = Field(default_factory=list, description="必须满足的条件（AND）")
#     should: list[QueryClause] = Field(default_factory=list, description="应该满足的条件（OR）")
#     must_not: list[QueryClause] = Field(default_factory=list, description="必须不满足的条件（NOT）")
#     minimum_should_match: int = Field(default=1, description="should 中最少需要匹配的数量")


# class DocumentQuery(BaseModel):
#     """文档查询 DSL"""

#     query: QueryClause | BoolQuery = Field(description="查询条件")
#     context: int = Field(default=1, description="返回匹配段落前后各N个段落作为上下文")
#     highlight: bool = Field(default=True, description="是否高亮匹配的关键词")
#     size: int = Field(default=50, description="最大返回段落数")


# region Tool Schema

# 样式数组索引常量（与前端 docxJsonConverter.js 保持一致）
# pStyle: [alignment, lineSpacing, indentLeft, indentRight, indentFirstLine, spaceBefore, spaceAfter, styleName, lineSpacingRule]
# rStyle: [fontName, fontSize, bold, italic, underline, underlineColor, color, highlight, strikethrough, superscript, subscript]
# cStyle: [rowSpan, colSpan, alignment, verticalAlignment]
# tStyle: [tableAlignment]


class Run(BaseModel):
    """格式块 - 一段具有相同格式的文字"""

    text: str = Field(description="文字内容")
    rStyle: list = Field(
        default_factory=lambda: ["宋体", 12, False, False, 0, "#000000", "#000000", 0, False, False, False],
        description="""字符样式数组，按顺序: [字体, 字号, 粗体, 斜体, 下划线, 下划线颜色, 颜色, 高亮, 删除线, 上标, 下标]
- 下划线: 0=无, 1=单线, 3=双线, 4=虚线, 6=粗线, 11=波浪线
- 下划线颜色/颜色: #RRGGBB 格式
- 高亮: 0=无, 1=黑, 2=蓝, 3=青绿, 4=鲜绿, 5=粉红, 6=红, 7=黄, 9=深蓝, 10=青, 11=绿, 12=紫罗兰, 13=深红, 14=深黄, 15=深灰, 16=浅灰""",
    )


class Paragraph(BaseModel):
    """段落"""

    pStyle: list = Field(
        default_factory=lambda: ["left", 12, 0, 0, 0, 0, 6, "正文", 0],
        description="""段落样式数组，按顺序: [对齐, 行距, 左缩进, 右缩进, 首行缩进, 段前, 段后, 样式名, 行距规则]
- 对齐: left/center/right/justify
- 行距规则: 0=多倍行距, 1=至少, 2=固定值""",
    )
    runs: list[Run] = Field(description="格式块数组")


class Cell(BaseModel):
    """表格单元格"""

    text: str = Field(description="单元格文本")
    cStyle: list = Field(
        default_factory=lambda: [1, 1, "left", "center"],
        description="单元格样式数组: [跨行数, 跨列数, 水平对齐(left/center/right), 垂直对齐(top/center/bottom)]",
    )


class Table(BaseModel):
    """表格"""

    rows: int = Field(description="行数")
    columns: int = Field(description="列数")
    cells: list[list[Cell]] = Field(description="单元格二维数组")
    tStyle: list = Field(
        default_factory=lambda: ["center"],
        description="表格样式数组: [表格对齐(left/center/right)]",
    )


class DocumentOutput(BaseModel):
    """文档输出结构"""

    paragraphs: list[Paragraph] = Field(description="段落数组")
    tables: list[Table] = Field(default_factory=list, description="表格数组")


# region tool


@tool
def request_document() -> str:
    """
    请求获取完整文档内容。

    当用户要求对文档进行任何操作或查看文档内容，但当前没有收到文档内容时，调用此工具请求前端发送完整文档。

    【调用场景】
    1. 操作类：
       - 用户说"润色全文"但没有提供文档内容
       - 用户说"修改第三段"但没有收到文档内容
       - 用户说"润色开头"但没有选中内容
       - 用户说"把这里改成..."但没有提供文档上下文

    2. 查看/分析类：
       - 用户说"看看这篇文档"但没有文档内容
       - 用户说"告诉我文档写了什么"但没有文档
       - 用户说"分析一下这个文档"但文档为空
       - 用户说"检查文档"、"总结文档内容"但没有收到文档

    3. 任何需要文档内容但 documentJson 为空或没有 paragraphs 的情况

    Returns:
        提示信息，前端收到后会自动解析并发送完整文档
    """

    # 获取流式输出 writer
    writer = get_stream_writer()
    # 发送请求文档的消息给前端（带 type 字段，前端可以识别）
    writer({"type": "request_document", "content": "📑 正在解析全文"})
    print("[request_document] 请求前端发送完整文档")
    return ""  # 返回空字符串，避免被当作普通文本输出


@tool
def generate_document(document: DocumentOutput) -> dict:
    """
    生成带格式的文档 JSON，用于输出到 Word 文档。

    【重要】格式属性必须100%原样复制！
    除非用户明确要求修改格式，否则所有格式属性（fontName, fontSize, alignment 等）必须与原文档完全一致。

    Args:
        document: 文档结构，包含段落和表格

    Returns:
        文档 JSON 对象
    """
    writer = get_stream_writer()
    # writer({"type": "status", "content": "正在生成文档..."}) # 没用

    # 生成完整的 JSON，所有属性都有值
    doc_dict = document.model_dump()

    # 保存到 example 文件夹
    try:
        from pathlib import Path
        from datetime import datetime

        example_dir = Path(__file__).parent.parent.parent / "example"
        example_dir.mkdir(exist_ok=True)

        # 生成带时间戳的文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = example_dir / f"generated_{timestamp}.json"

        # 保存 JSON 文件（带缩进方便调试查看）
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(doc_dict, f, ensure_ascii=False, indent=2)

        print(f"[生成文档] JSON 已保存到: {output_file}")
    except Exception as e:
        print(f"[生成文档] 保存文件失败: {e}")

    writer({"type": "status", "content": "✅ 文档已生成"})
    return doc_dict


# @tool
# def locate_in_document(query: DocumentQuery) -> dict:
#     """
#     在文档中定位需要修改的内容（使用 Query DSL）。

#     根据用户请求生成搜索条件，前端会根据条件在全文中搜索并返回匹配的段落。

#     【Query DSL 示例】

#     1. 搜索包含关键词的段落：
#        {"query": {"match": {"field": "text", "query": "公司名称"}}}

#     2. 搜索特定章节（按标题样式）：
#        {"query": {"match": {"field": "styleName", "query": "标题"}}}

#     3. 搜索前5段：
#        {"query": {"range": {"field": "index", "gte": 0, "lte": 4}}}

#     4. 搜索最后一段（用负数表示倒数）：
#        {"query": {"range": {"field": "index", "gte": -1}}}

#     5. 组合条件 - 搜索标题中包含"第三章"的段落：
#        {"query": {"bool": {"must": [
#            {"match": {"field": "text", "query": "第三章"}},
#            {"match": {"field": "styleName", "query": "标题"}}
#        ]}}}

#     6. 搜索全文：
#        {"query": {"match_all": {}}}

#     7. 搜索所有高亮文字：
#        {"query": {"term": {"field": "hasHighlight", "value": true}}}

#     Args:
#         query: Query DSL 查询条件

#     Returns:
#         查询条件字典，前端用于执行实际搜索
#     """
#     return query.model_dump()


# region System Prompt

# LOCATOR_AGENT_PROMPT = """你是文档定位助手。你的任务是分析用户的修改请求，生成 Query DSL 来定位需要修改的内容。

# 【你的工作流程】
# 1. 理解用户想修改什么内容
# 2. 调用 locate_in_document 工具，生成 Query DSL
# 3. 不要直接修改内容，只负责定位

# 【Query DSL 语法说明】

# 1. **match** - 匹配查询（模糊搜索）
#    ```json
#    {"query": {"match": {"field": "text", "query": "关键词"}}}
#    ```
#    - field 可选值: "text"(段落文本), "styleName"(样式名), "fontName"(字体名)

# 2. **range** - 范围查询（按位置）
#    ```json
#    {"query": {"range": {"field": "index", "gte": 0, "lte": 10}}}
#    ```
#    - field 可选值: "index"(段落索引,从0开始), "position"(字符位置)
#    - 支持: gte(>=), lte(<=), gt(>), lt(<)
#    - 负数表示倒数，如 -1 表示最后一段

# 3. **term** - 精确匹配（布尔值）
#    ```json
#    {"query": {"term": {"field": "hasHighlight", "value": true}}}
#    ```
#    - field 可选值: "isEmpty", "isHeading", "isBold", "hasHighlight"

# 4. **match_all** - 匹配全部
#    ```json
#    {"query": {"match_all": {}}}
#    ```

# 5. **bool** - 布尔组合
#    ```json
#    {"query": {"bool": {
#        "must": [...],      // AND - 必须满足
#        "should": [...],    // OR - 任一满足
#        "must_not": [...]   // NOT - 必须不满足
#    }}}
#    ```

# 【常见场景映射】

# | 用户说 | Query DSL |
# |--------|-----------|
# | "修改开头" | {"query": {"range": {"field": "index", "gte": 0, "lte": 2}}} |
# | "修改结尾" | {"query": {"range": {"field": "index", "gte": -3}}} |
# | "把'公司'改成'企业'" | {"query": {"match": {"field": "text", "query": "公司"}}} |
# | "修改第三章" | {"query": {"match": {"field": "text", "query": "第三章"}}} |
# | "润色全文" | {"query": {"match_all": {}}} |
# | "修改所有标题" | {"query": {"match": {"field": "styleName", "query": "标题"}}} |
# | "修改第5段" | {"query": {"range": {"field": "index", "gte": 4, "lte": 4}}} |
# | "高亮的部分" | {"query": {"term": {"field": "hasHighlight", "value": true}}} |

# 【参数说明】
# - context: 返回匹配段落前后各N个段落（默认1）
# - size: 最大返回段落数（默认50）

# 【输出要求】
# 必须调用 locate_in_document 工具，不要直接回复文字。
# """

WRITER_ASK_PROMPT = """你是专业的文档处理和写作助手。你可以：
1. 润色、重写、翻译、扩写、缩写文档内容
2. 调整格式（字体、字号、对齐、缩进等）
3. 回答用户的问题和进行日常对话

请用简洁、清晰、友好的语气回复。如果不确定答案，请诚实说明。"""

WRITER_AGENT_PROMPT = """你是专业的文档处理和写作助手。你可以：
1. 润色、重写、翻译、扩写、缩写文档内容
2. 调整格式（字体、字号、对齐、缩进等）
3. 回答用户的问题和进行日常对话

【工具使用规则 - 非常重要】

🔵 **必须调用 request_document 工具的情况：**
只要用户提到"文档"、"文章"、"这篇"、"全文"、"内容"等词，且你没有收到任何文档内容，就**必须立即调用 request_document**！

具体场景：
- "这是一篇什么文章" → 调用 request_document
- "这篇文档讲了什么" → 调用 request_document
- "看看这篇文档" → 调用 request_document
- "润色全文" → 调用 request_document
- "修改第三段" → 调用 request_document
- "分析一下文档" → 调用 request_document
- "总结文档内容" → 调用 request_document
- "检查一下" → 调用 request_document

⚠️ **关键判断**：如果用户的请求涉及文档/文章，但你没有看到任何文档JSON内容，就调用 request_document！

✅ **调用 generate_document 工具的情况：**
用户**已经提供了文档内容**（你能看到 paragraphs 数据），并且要求修改/润色/生成

❌ **不调用任何工具的情况：**
- 纯粹的问候（"你好"）
- 与文档无关的问题（"什么是AI"、"今天天气怎么样"）
- 询问你的功能（"你能干什么"）

【工具调用要求】
调用工具时：
1. 先用1-2句话说明你要做什么
2. 然后**立即调用工具**
"""

SUMMARY_PROMPT = """你是文档内容分析助手。请分析生成的文档内容，提炼出主要的内容要点。

要求：
1. 列出生成的主要内容（如：生成了第一点...、第二点...）
2. 如果是单段内容，总结核心主题
3. 简洁明了，不要重复原文
4. 使用分点格式（用数字或序号）
5. 使用友好的语气

示例：
- 如果是多点内容：已生成3点内容：1. XXX 2. YYY 3. ZZZ
- 如果是单段内容：已生成一段关于XXX的内容
- 如果是文章：已生成一篇关于XXX的文章，包含...几个部分"""

# ============== 创建 LLM 实例 ==============


def create_llm(model_name: str) -> ChatOpenAI:
    """创建 LLM 实例，使用 llm_client 统一管理配置"""
    provider_info = LLMClientManager.get_provider_info(model_name)

    return ChatOpenAI(
        model=model_name,
        openai_api_key=provider_info.api_key,
        openai_api_base=provider_info.base_url,
        temperature=0.7,
        streaming=True,  # 启用流式输出
    )


# ============== LangGraph 节点工厂 ==============


def create_writer_agent_node(llm_with_tools):
    """创建 writer_agent 节点（使用闭包传递 llm_with_tools）"""

    def writer_agent(state: MessagesState) -> dict:
        """Writer Agent - 处理文档生成和修改请求"""
        print("[Writer Agent] 开始处理")
        response = llm_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    return writer_agent


def create_summary_agent_node(llm):
    """创建 summary_agent 节点（使用闭包传递 llm）"""

    def summary_agent(state: MessagesState) -> dict:
        """Summary Agent - 总结文档修改内容"""
        print("[Summary Agent] 开始总结")
        writer = get_stream_writer()

        # 从消息历史中提取用户请求和工具结果
        user_request = ""
        document_content = ""

        for msg in state["messages"]:
            if isinstance(msg, HumanMessage):
                # 提取用户的原始请求（去掉 JSON 部分）
                content = msg.content
                if "要求：" in content:
                    user_request = content.split("要求：")[-1].split("\n")[0].strip()
                else:
                    user_request = content[:200]  # 取前200字符
            elif isinstance(msg, ToolMessage):
                # 提取工具生成的实际内容
                try:
                    doc = json.loads(msg.content)
                    paragraphs = doc.get("paragraphs", [])

                    # 提取所有段落的文本内容
                    text_parts = []
                    for para in paragraphs:
                        para_text = para.get("text", "")
                        if not para_text and para.get("runs"):
                            # 从 runs 中拼接文本
                            para_text = "".join([run.get("text", "") for run in para.get("runs", [])])
                        if para_text:
                            text_parts.append(para_text)

                    document_content = "\n".join(text_parts)

                    # 如果有表格，也提取表格内容
                    tables = doc.get("tables", [])
                    if tables:
                        document_content += f"\n\n[包含 {len(tables)} 个表格]"

                except Exception as e:
                    print(f"[Summary Agent] 提取内容失败: {e}")
                    document_content = "文档已生成"

        # 构建总结请求
        summary_messages = [
            SystemMessage(content=SUMMARY_PROMPT),
            HumanMessage(
                content=f"用户请求：{user_request}\n\n生成的内容：\n{document_content}\n\n请分析并总结：生成了哪几点内容？"
            ),
        ]

        writer({"type": "status", "content": "📝 正在总结修改..."})
        response = llm.invoke(summary_messages)
        print(f"[Summary Agent] 总结完成: {response.content[:100]}...")

        return {"messages": [response]}

    return summary_agent


def call_tools(state: MessagesState) -> dict:
    """执行工具调用"""

    last_message = state["messages"][-1]
    results = []

    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        print(f"[call_tools] 执行工具: {tool_name}")

        if tool_name == "generate_document":
            result = generate_document.invoke(tool_call["args"])
            results.append(ToolMessage(content=json.dumps(result, ensure_ascii=False), tool_call_id=tool_call["id"]))
        elif tool_name == "request_document":
            result = request_document.invoke(tool_call["args"])
            results.append(ToolMessage(content=result, tool_call_id=tool_call["id"]))

    return {"messages": results}


def should_call_tools(state: MessagesState) -> str:
    """判断是否需要调用工具"""
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        print("[Router] -> call_tools")
        return "call_tools"
    print("[Router] -> END (闲聊模式)")
    return END


def should_summarize(state: MessagesState) -> str:
    """判断工具执行后是否需要进入总结节点"""
    last_message = state["messages"][-1]
    if isinstance(last_message, ToolMessage):
        content = last_message.content
        # request_document 返回空字符串，不需要总结
        if not content:
            print("[Router] -> END (request_document 已发送)")
            return END
    print("[Router] -> summary_agent")
    return "summary_agent"


# ============== 构建 LangGraph ==============


def build_graph(llm_with_tools, llm):
    """
    构建 LangGraph 工作流

    流程：
    START -> writer_agent
             ├─ (有tool_calls) -> call_tools
             │                    ├─ (generate_document) -> summary_agent -> END
             │                    └─ (request_document) -> END
             └─ (无tool_calls，闲聊) -> END
    """
    graph = StateGraph(MessagesState)

    # 添加节点
    graph.add_node("writer_agent", create_writer_agent_node(llm_with_tools))
    graph.add_node("call_tools", call_tools)
    graph.add_node("summary_agent", create_summary_agent_node(llm))

    # 添加边
    graph.add_edge(START, "writer_agent")
    graph.add_conditional_edges("writer_agent", should_call_tools, {"call_tools": "call_tools", END: END})
    # call_tools 后根据工具类型决定是否进入总结
    graph.add_conditional_edges("call_tools", should_summarize, {"summary_agent": "summary_agent", END: END})
    graph.add_edge("summary_agent", END)  # 总结后结束

    return graph.compile()


# region 主处理函数


async def process_writing_request_stream(
    message: str,
    document_json: dict | None = None,
    history: list | None = None,
    model: str | None = None,
    mode: str | None = None,
) -> AsyncGenerator[str, None]:
    """
    使用 LangGraph 处理写作请求（流式输出）

    Args:
        message: 用户消息
        document_json: 用户选中的文档 JSON
        history: 历史消息
        model: 用户选择的模型
        mode: 对话模式（agent/ask）

    Yields:
        SSE 格式的流式输出
    """
    print("[LangGraph Agent] 开始处理请求")
    print(f"[LangGraph Agent] 模式: {mode}")

    model_name = resolve_model(model or "auto")
    llm = create_llm(model_name)

    # 根据模式决定是否绑定工具
    is_ask_mode = mode == "ask"

    if is_ask_mode:
        # ask 模式：纯对话
        llm_for_agent = llm.bind_tools([request_document])
        print("[LangGraph Agent] ask 模式，已绑定 request_document 工具")
    else:
        # agent 模式：绑定工具，可以生成文档或请求全文
        llm_for_agent = llm.bind_tools([generate_document, request_document])
        print("[LangGraph Agent] agent 模式，已绑定 generate_document 和 request_document 工具")

    # 构建图
    app = build_graph(llm_for_agent, llm)

    try:
        # 根据模式选择 System Prompt
        if is_ask_mode:
            system_prompt = WRITER_ASK_PROMPT
        else:
            system_prompt = WRITER_AGENT_PROMPT

        messages = [SystemMessage(content=system_prompt)]

        # 暂时不添加历史消息
        # # 添加历史
        # for msg in (history or [])[-6:]:
        #     if isinstance(msg, dict) and "role" in msg and "content" in msg:
        #         if msg["role"] == "user":
        #             messages.append(HumanMessage(content=msg["content"]))
        #         else:
        #             messages.append(AIMessage(content=msg["content"]))

        # 构建用户消息
        user_content = message
        if document_json and document_json.get("paragraphs"):
            # 只有在有实际段落内容时才添加文档 JSON
            # 使用新版数组格式，只保留必要字段
            simplified = {"paragraphs": []}
            for para in document_json.get("paragraphs", []):
                simplified["paragraphs"].append(
                    {
                        "text": para.get("text", ""),
                        "pStyle": para.get("pStyle", ["left", 12, 0, 0, 0, 0, 6, "", 0]),
                        "runs": para.get("runs", []),
                    }
                )
            if document_json.get("tables"):
                simplified["tables"] = document_json["tables"]

            # 使用压缩 JSON（无缩进、无多余空格）节省 token
            compact_json = json.dumps(simplified, ensure_ascii=False, separators=(",", ":"))
            user_content = f"文档JSON（pStyle/rStyle必须原样复制）：{compact_json}\n\n要求：{message}\n\n⚠️ 调用 generate_document 工具返回修改后的文档！"

        messages.append(HumanMessage(content=user_content))

        print(f"[LangGraph Agent] 消息数量: {len(messages)}")

        # 在异步环境中使用同步的 stream
        loop = asyncio.get_running_loop()

        # 创建队列用于在线程间传递数据
        queue = asyncio.Queue()
        has_tool_result = False

        def run_stream():
            """在独立线程中运行同步的 stream"""
            try:
                response = app.stream({"messages": messages}, stream_mode=["messages", "custom", "updates"])

                for stream_item in response:
                    # 将数据放入队列
                    asyncio.run_coroutine_threadsafe(queue.put(stream_item), loop)

                # 发送结束信号
                asyncio.run_coroutine_threadsafe(queue.put(None), loop)
            except Exception as e:
                asyncio.run_coroutine_threadsafe(queue.put(("error", str(e))), loop)

        # 在线程池中启动同步 stream（不等待完成，让它并行运行）
        import concurrent.futures

        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        executor.submit(run_stream)

        # 从队列中读取并处理数据（与生产者并行）
        while True:
            stream_item = await queue.get()

            if stream_item is None:
                # 结束信号
                break

            if isinstance(stream_item, tuple) and stream_item[0] == "error":
                raise Exception(stream_item[1])

            # stream_mode='messages' 和 'custom' 返回 tuple
            # stream_mode='updates' 返回 dict
            if isinstance(stream_item, tuple):
                input_type, chunk = stream_item

                if input_type == "messages":
                    # AI 的输出内容（流式 token）
                    if chunk and len(chunk) > 0:
                        msg = chunk[0]
                        content = msg.content

                        # 检查是否有 reasoning_content（thinking 内容）
                        # DeepSeek R1 等模型会在 additional_kwargs 中返回思考过程
                        # if hasattr(msg, "additional_kwargs"):
                        #     reasoning = msg.additional_kwargs.get("reasoning_content", "")
                        #     if reasoning:
                        #         yield f"data: {json.dumps({'type': 'thinking', 'content': reasoning}, ensure_ascii=False)}\n\n"

                        # 检查 AIMessage 是否决定调用工具
                        # if isinstance(msg, AIMessage) and hasattr(msg, "tool_calls") and msg.tool_calls:
                        #     tool_names = [tc.get("name", "unknown") for tc in msg.tool_calls]
                        #     print(f"[LangGraph] 🎯 模型决定调用工具: {tool_names}")
                        #     yield f"data: {json.dumps({'type': 'status', 'content': '🎯 AI决定生成文档...'}, ensure_ascii=False)}\n\n"

                        # 检查是否是 ToolMessage（工具返回的结果）
                        if isinstance(msg, ToolMessage):
                            # 过滤 request_document 的返回值（不是 JSON，只是路由标记）
                            if content == "request_document":
                                print(f"[LangGraph] ⏭️ 跳过 request_document 工具返回值")
                                continue

                            try:
                                doc_json = json.loads(content)
                                if "paragraphs" in doc_json:
                                    print(f"[LangGraph] ✅ 从 messages 流提取到工具结果")
                                    yield f"data: {json.dumps({'type': 'json', 'content': doc_json}, ensure_ascii=False)}\n\n"
                                    has_tool_result = True
                                    continue
                            except json.JSONDecodeError:
                                pass

                        # 检查是否是 AIMessage 且内容看起来像 JSON（工具调用后 LLM 可能直接输出 JSON）
                        # if content and content.strip().startswith('{"paragraphs"'):
                        #     try:
                        #         doc_json = json.loads(content)
                        #         if "paragraphs" in doc_json:
                        #             print(f"[LangGraph] ✅ 从文本中提取到 JSON 文档")
                        #             yield f"data: {json.dumps({'type': 'json', 'content': doc_json}, ensure_ascii=False)}\n\n"
                        #             has_tool_result = True
                        #             continue
                        #     except json.JSONDecodeError:
                        #         pass

                        # 普通文本输出
                        if content:
                            # print(f"[LangGraph] 文本块: {content[:50]}...")
                            yield f"data: {json.dumps({'type': 'text', 'content': content}, ensure_ascii=False)}\n\n"

                elif input_type == "custom":
                    # 工具执行的输出内容（get_stream_writer）
                    print(f"[LangGraph] 自定义输出: {chunk}")
                    # 将状态消息发送给前端
                    if chunk:
                        # 如果 chunk 是字典（如 request_document 发送的），直接转发
                        if isinstance(chunk, dict):
                            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                        else:
                            # 普通字符串包装成 status 类型
                            yield f"data: {json.dumps({'type': 'status', 'content': str(chunk)}, ensure_ascii=False)}\n\n"

            elif isinstance(stream_item, dict):
                # updates 模式：包含节点执行的完整更新
                for node_name, node_output in stream_item.items():
                    # 检测节点状态变化（用于调试）
                    if node_name == "call_model":
                        print(f"[LangGraph] 进入 call_model 节点")
                    elif node_name == "call_tools":
                        print(f"[LangGraph] 进入 call_tools 节点")

                    if node_name == "call_tools" and "messages" in node_output:
                        # 提取工具调用结果
                        for msg in node_output["messages"]:
                            if isinstance(msg, ToolMessage):
                                try:
                                    # ToolMessage 的 content 是 JSON 字符串
                                    doc_json = json.loads(msg.content)
                                    if "paragraphs" in doc_json and not has_tool_result:
                                        print(f"[LangGraph] ✅ 从 updates 提取到工具结果")
                                        yield f"data: {json.dumps({'type': 'json', 'content': doc_json}, ensure_ascii=False)}\n\n"
                                        has_tool_result = True
                                except json.JSONDecodeError:
                                    print(f"[LangGraph] ⚠️ 工具结果不是有效JSON")

        if not has_tool_result:
            print(f"[LangGraph] ⚠️ 未检测到工具调用结果")
            # writer = get_stream_writer()
            # writer("⚠️ 没有检测到生成文档，模型可能不支持")
            yield f"data: {json.dumps({'type': 'status', 'content': '⚠️ 没有检测到生成文档，模型可能不支持'}, ensure_ascii=False)}\n\n"

        yield "data: [DONE]\n\n"

    except Exception as e:
        print(f"[LangGraph Error] {e}")
        import traceback

        traceback.print_exc()
        yield f"data: {json.dumps({'type': 'text', 'content': f'错误: {str(e)}'}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"


# ============== 两阶段处理：定位 + 修改 ==============


# async def process_locate_request(
#     message: str,
#     document_summary: dict | None = None,
#     model: str | None = None,
# ) -> dict:
#     """
#     阶段1：定位 - 分析用户意图，生成 Query DSL

#     Args:
#         message: 用户消息
#         document_summary: 文档摘要（段落数、标题列表等，不是全文）
#         model: 模型名称

#     Returns:
#         包含 Query DSL 的字典，或纯文本回复
#     """
#     print("[Locator Agent] 开始定位")

#     model_name = resolve_model(model or "auto")
#     llm = create_llm(model_name)

#     # 绑定定位工具
#     llm_with_tools = llm.bind_tools([locate_in_document])

#     # 构建摘要信息
#     summary_text = "文档概要：\n"
#     if document_summary:
#         summary_text += f"- 总段落数: {document_summary.get('paragraphCount', '未知')}\n"
#         summary_text += f"- 表格数: {document_summary.get('tableCount', 0)}\n"

#         headings = document_summary.get("headings", [])
#         if headings:
#             summary_text += f"- 标题列表:\n"
#             for h in headings[:20]:  # 最多显示20个标题
#                 summary_text += f"  [{h.get('index')}] {h.get('text', '')}\n"

#         stats = document_summary.get("stats", {})
#         if stats.get("highlightCount"):
#             summary_text += f"- 高亮段落数: {stats['highlightCount']}\n"

#         first_para = document_summary.get("firstParagraph", "")
#         if first_para:
#             summary_text += f"- 首段预览: {first_para[:100]}...\n"

#     messages = [
#         SystemMessage(content=LOCATOR_AGENT_PROMPT),
#         HumanMessage(content=f"{summary_text}\n用户请求: {message}\n\n请生成 Query DSL 来定位需要修改的内容。"),
#     ]

#     response = llm_with_tools.invoke(messages)

#     # 检查是否调用了工具
#     if hasattr(response, "tool_calls") and response.tool_calls:
#         tool_call = response.tool_calls[0]
#         query_dsl = tool_call.get("args", {})
#         print(f"[Locator Agent] 生成 Query DSL: {json.dumps(query_dsl, ensure_ascii=False)}")
#         return {"type": "query", "queryDSL": query_dsl, "message": response.content or "已生成搜索条件"}

#     # 没有调用工具，返回纯文本
#     return {"type": "text", "content": response.content}


# async def process_modify_with_context(
#     message: str,
#     matched_paragraphs: list,
#     original_indices: list[int],
#     model: str | None = None,
# ) -> AsyncGenerator[str, None]:
#     """
#     阶段2：修改 - 只处理匹配的段落

#     Args:
#         message: 用户的原始修改请求
#         matched_paragraphs: 匹配的段落数组（已包含 index 和 isTarget 标记）
#         original_indices: 原始段落索引列表
#         model: 模型名称

#     Yields:
#         SSE 格式的流式输出
#     """
#     print(f"[Modify Agent] 开始修改，共 {len(matched_paragraphs)} 个段落")

#     # 构建精简的文档 JSON（只包含需要修改的段落）
#     document_json = {
#         "paragraphs": matched_paragraphs,
#         "_meta": {
#             "originalIndices": original_indices,
#             "isPartial": True,  # 标记这是部分文档
#         },
#     }

#     # 复用现有的处理函数
#     async for chunk in process_writing_request_stream(
#         message=message, document_json=document_json, model=model, mode="agent"
#     ):
#         yield chunk


# async def process_two_phase_stream(
#     message: str,
#     document_summary: dict | None = None,
#     model: str | None = None,
# ) -> AsyncGenerator[str, None]:
#     """
#     两阶段流式处理：先定位，再等待前端提供匹配内容

#     这个函数只处理第一阶段（定位），返回 Query DSL
#     前端收到后执行搜索，然后调用 process_modify_with_context 完成修改

#     Args:
#         message: 用户消息
#         document_summary: 文档摘要
#         model: 模型名称

#     Yields:
#         SSE 格式的流式输出
#     """
#     yield f"data: {json.dumps({'type': 'status', 'content': '🔍 正在分析修改位置...'}, ensure_ascii=False)}\n\n"

#     try:
#         result = await process_locate_request(message, document_summary, model)

#         if result["type"] == "query":
#             # 返回 Query DSL，前端执行搜索
#             yield f"data: {json.dumps({'type': 'query', 'queryDSL': result['queryDSL'], 'message': result.get('message', '')}, ensure_ascii=False)}\n\n"
#         else:
#             # 纯文本回复（可能是闲聊）
#             yield f"data: {json.dumps({'type': 'text', 'content': result.get('content', '')}, ensure_ascii=False)}\n\n"

#         yield "data: [DONE]\n\n"

#     except Exception as e:
#         print(f"[Two Phase Error] {e}")
#         import traceback

#         traceback.print_exc()
#         yield f"data: {json.dumps({'type': 'error', 'content': f'定位失败: {str(e)}'}, ensure_ascii=False)}\n\n"
#         yield "data: [DONE]\n\n"
