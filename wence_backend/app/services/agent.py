"""
文档处理 Agent - 使用 LangGraph + 流式输出
"""

import asyncio
import json
from collections.abc import AsyncGenerator

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.config import get_stream_writer
from langgraph.graph import END, START, MessagesState, StateGraph
from pydantic import BaseModel, Field

from app.services.llm_client import LLMClientManager, resolve_model

# ============== Pydantic 模型定义（用于 Tool Schema）==============

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
        #                       [字体,  字号, 粗体,  斜体,  下划线, 下划线颜色, 颜色,    高亮, 删除线,  上标, 下标]
        description="字符样式数组: [字体, 字号, 粗体, 斜体, 下划线, 下划线颜色, 颜色, 高亮, 删除线, 上标, 下标]",
    )


class Paragraph(BaseModel):
    """段落"""

    text: str | None = Field(None, description="段落完整文本（可选，可从 runs 拼接）")
    pStyle: list = Field(
        default_factory=lambda: ["left", 12, 0, 0, 0, 0, 6, "正文", 0],
        description="段落样式数组: [对齐, 行距, 左缩进, 右缩进, 首行缩进, 段前, 段后, 样式名, 行距规则]",
    )
    runs: list[Run] = Field(description="格式块数组")


class Cell(BaseModel):
    """表格单元格"""

    text: str = Field(description="单元格文本")
    cStyle: list = Field(
        default_factory=lambda: [1, 1, "left", "center"], description="单元格样式数组: [跨行, 跨列, 水平对齐, 垂直对齐]"
    )


class Table(BaseModel):
    """表格"""

    rows: int = Field(description="行数")
    columns: int = Field(description="列数")
    cells: list[list[Cell]] = Field(description="单元格二维数组")
    tStyle: list = Field(default_factory=lambda: ["center"], description="表格样式数组: [表格对齐]")


class DocumentOutput(BaseModel):
    """文档输出结构"""

    paragraphs: list[Paragraph] = Field(description="段落数组")
    tables: list[Table] = Field(default_factory=list, description="表格数组")


# ============== Tool 定义 ==============


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

    return doc_dict


# ============== System Prompt ==============

AGENT_PROMPT = """你是专业的文档处理和写作助手。你可以：
1. 润色、重写、翻译、扩写、缩写文档内容
2. 调整格式（字体、字号、对齐、缩进等）
3. 回答用户的问题和进行日常对话

【工具使用规则 - 非常重要】
✅ **必须调用 generate_document 工具的情况：**
- 用户要求**生成**、**创建**、**写**任何文档内容（文章、报告、证明、论文等）
- 用户要求**修改**、**润色**、**重写**、**翻译**现有文档
- 用户要求**扩写**、**缩写**、**续写**文档
- 用户要求调整文档**格式**（字体、对齐等）

❌ **不调用工具的情况：**
- 用户只是问问题（"什么是..."、"如何..."、"为什么..."）
- 纯聊天对话（"你好"、"谢谢"）

🔴【工具调用要求 - 必须遵守】🔴
如果需要调用工具，你必须：
1. 先用2-3句话说明你要做什么
2. 然后**立即调用 generate_document 工具**生成完整的文档 JSON

⚠️ **禁止直接输出 JSON 文本！必须通过工具调用返回 JSON！**

【格式原则】
- 如果用户只要求改内容：所有格式属性必须100%原样复制
- 如果用户要求改格式：可以修改格式属性，但内容保持不变
- 如果是生成新文档（无原文档）：使用默认格式

【JSON 格式说明 - 数组格式节省 token】
使用数组表示样式，按固定顺序：
- pStyle: [对齐, 行距, 左缩进, 右缩进, 首行缩进, 段前, 段后, 样式名, 行距规则]
  * 对齐: left/center/right/justify
  * 行距规则: 0=多倍行距, 1=至少, 2=固定值
- rStyle: [字体, 字号, 粗体, 斜体, 下划线, 下划线颜色, 颜色, 高亮, 删除线, 上标, 下标]
  * 下划线: 0=无, 1=单线, 3=双线, 4=虚线, 6=粗线, 7=粗虚线, 11=波浪线, 27=粗波浪线 (支持0-15的值)
  * 下划线颜色: #RRGGBB 格式
  * 颜色: #RRGGBB 格式
  * 高亮: 0=无, 1-16=颜色索引 (1=黑、2=蓝、3=青绿、4=鲜绿、5=粉红、6=红、7=黄、9=深蓝、10=青、11=绿、12=紫罗兰、13=深红、14=深黄、15=深灰、16=浅灰)
- cStyle: [跨行, 跨列, 水平对齐, 垂直对齐]
- tStyle: [表格对齐]

【扩写新增段落时】
新段落要沿用相邻段落的完整格式（复制 pStyle 和 rStyle）。"""


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


# ============== Summary Agent Prompt ==============

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

        writer("📝 正在总结修改...")
        response = llm.invoke(summary_messages)
        print(f"[Summary Agent] 总结完成: {response.content[:100]}...")

        return {"messages": [response]}

    return summary_agent


def call_tools(state: MessagesState) -> dict:
    """执行工具调用"""
    writer = get_stream_writer()

    last_message = state["messages"][-1]
    results = []

    for tool_call in last_message.tool_calls:
        # 执行工具
        if tool_call["name"] == "generate_document":
            result = generate_document.invoke(tool_call["args"])
            results.append(ToolMessage(content=json.dumps(result, ensure_ascii=False), tool_call_id=tool_call["id"]))

    writer("✅ 文档已生成")
    return {"messages": results}


def should_call_tools(state: MessagesState) -> str:
    """判断是否需要调用工具"""
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        print("[Router] -> call_tools")
        return "call_tools"
    print("[Router] -> END (闲聊模式)")
    return END


# ============== 构建 LangGraph ==============


def build_graph(llm_with_tools, llm):
    """
    构建 LangGraph 工作流

    流程：
    START -> writer_agent
             ├─ (有tool_calls) -> call_tools -> summary_agent -> END
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
    graph.add_edge("call_tools", "summary_agent")  # 工具执行后进入总结
    graph.add_edge("summary_agent", END)  # 总结后结束

    return graph.compile()


# ============== 主处理函数 ==============


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

    # 绑定工具到模型（用于 writer_agent）
    llm_with_tools = llm.bind_tools([generate_document])

    # 构建图（传入 llm_with_tools 和 llm）
    app = build_graph(llm_with_tools, llm)

    try:
        # 构建消息
        messages = [SystemMessage(content=AGENT_PROMPT)]

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
        if document_json:
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
            yield f"data: {json.dumps({'type': 'status', 'content': '⚠️ 没有检测到生成文档，模型可能不支持'}, ensure_ascii=False)}\n\n"

        yield "data: [DONE]\n\n"

    except Exception as e:
        print(f"[LangGraph Error] {e}")
        import traceback

        traceback.print_exc()
        yield f"data: {json.dumps({'type': 'text', 'content': f'错误: {str(e)}'}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
