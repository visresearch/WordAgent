"""
文档处理 Agent - 使用 LangGraph ReAct 单一智能体 + 流式输出
"""

import asyncio
import concurrent.futures
import contextvars
import json
import traceback
from collections.abc import AsyncGenerator

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.config import get_stream_writer
from langgraph.graph import END, START, MessagesState, StateGraph
from pydantic import BaseModel, Field

from app.services.llm_client import LLMClientManager, resolve_model

# ============== 工具回调等待机制 ==============
# 用于 WebSocket 模式下，agent 调用 tool 后等待前端回传结果

# 存储每个会话的等待队列：{session_id: asyncio.Queue}
_pending_tool_requests: dict[str, asyncio.Queue] = {}
# 存储每个会话的事件循环引用（供 tool 在同步线程中回到异步）
_pending_loops: dict[str, asyncio.AbstractEventLoop] = {}
# 当前线程使用的 session_id（通过 contextvars 传递到 tool 函数中）
_current_session_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("_current_session_id", default=None)


def create_tool_request(session_id: str) -> asyncio.Queue:
    """为一个会话创建等待队列"""
    q = asyncio.Queue()
    _pending_tool_requests[session_id] = q
    return q


def register_loop(session_id: str, loop: asyncio.AbstractEventLoop):
    """注册会话使用的事件循环（供 tool 函数中跨线程调用）"""
    _pending_loops[session_id] = loop


def cleanup_tool_request(session_id: str):
    """清理会话的等待队列"""
    _pending_tool_requests.pop(session_id, None)
    _pending_loops.pop(session_id, None)


async def submit_tool_response(session_id: str, data: dict):
    """前端通过 WebSocket 回传工具结果时调用"""
    q = _pending_tool_requests.get(session_id)
    if q:
        await q.put(data)
    else:
        print(f"[ToolCallback] ⚠️ 找不到 session {session_id} 的等待队列")


# region Tools Schema

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


# region Tools 定义


@tool
def read_document(startPos: int = -1, endPos: int = -1) -> str:
    """
    读取文档内容。通过 WebSocket 请求前端解析指定范围的文档并返回。

    Args:
        startPos: 文档读取起始位置（字符位置）。-1 表示从文档开头开始。
        endPos: 文档读取结束位置（字符位置）。-1 表示到文档结尾。
        两个都传 -1 表示读取全文。

    【调用场景】
    1. 读取全文（startPos=-1, endPos=-1）：
       - 用户说"润色全文"但没有提供文档内容
       - 用户说"看看这篇文档"但没有文档内容
       - 用户说"分析一下文档"但文档为空
       - 用户说"总结文档内容"但没有收到文档

    2. 读取指定范围：
       - 当用户选中了部分内容并要求操作时
       - 当需要读取文档特定位置的内容时

    3. 任何需要文档内容但 documentJson 为空或没有 paragraphs 的情况

    Returns:
        文档 JSON 字符串（包含 paragraphs 等），或空字符串
    """
    writer = get_stream_writer()
    writer({"type": "read_document", "content": "📑 正在读取文档", "startPos": startPos, "endPos": endPos})
    print(f"[read_document] 请求前端发送文档 (startPos={startPos}, endPos={endPos})")

    # 检查是否在 WebSocket 会话中（有 session_id）
    session_id = _current_session_id.get(None)
    if session_id:
        q = _pending_tool_requests.get(session_id)
        if q:
            print(f"[read_document] WebSocket 模式，等待前端回传文档 (session={session_id})")

            loop = _pending_loops.get(session_id)
            if loop:
                future = asyncio.run_coroutine_threadsafe(
                    asyncio.wait_for(q.get(), timeout=60),
                    loop,
                )
                try:
                    result = future.result(timeout=65)
                    doc_json = result.get("documentJson", {})
                    if doc_json and doc_json.get("paragraphs"):
                        print(f"[read_document] ✅ 收到文档，段落数: {len(doc_json['paragraphs'])}")
                        writer({"type": "status", "content": "✅ 文档读取完成"})
                        return json.dumps(doc_json, ensure_ascii=False)
                    else:
                        print("[read_document] ⚠️ 收到空文档")
                        writer({"type": "status", "content": "⚠️ 文档为空"})
                        return ""
                except (TimeoutError, concurrent.futures.TimeoutError):
                    print("[read_document] ⏰ 等待文档超时")
                    writer({"type": "status", "content": "⏰ 等待文档超时"})
                    return ""
                except Exception as e:
                    print(f"[read_document] ❌ 等待文档出错: {e}")
                    return ""

    # 非 WebSocket 模式（无 session_id），无法双向通信获取文档
    print("[read_document] ⚠️ 非 WebSocket 模式，无法请求文档")
    return ""


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
    doc_dict = document.model_dump()
    writer({"type": "status", "content": "✅ 文档已生成"})
    # Python 的 dict 就是字典，键值对的数据结构，类似 JavaScript 的 Object
    return doc_dict


@tool
def grep_document(keyword: str) -> str:
    """
    搜索文档内容。根据关键词搜索文档并返回相关内容。

    Args:
        keyword: 搜索关键词

    Returns:
        搜索结果字符串
    """
    # todo
    # 这里可以实现一个简单的搜索逻辑，或者直接请求前端进行搜索
    writer = get_stream_writer()
    writer({"type": "grep_document", "content": f"🔍 正在搜索文档: {keyword}"})
    print(f"[grep_document] 请求前端搜索文档 (keyword={keyword})")

    # 模拟返回搜索结果
    return f"搜索结果: 找到与 '{keyword}' 相关的内容..."


@tool
def web_fetch(url: str) -> str:
    """
    web_fetch 工具 - 根据 URL 获取网页内容

    Args:
        url: 目标网页 URL

    Returns:
        网页内容字符串
    """
    # todo
    # 这里可以实现一个简单的网页抓取逻辑，或者直接请求前端进行抓取
    writer = get_stream_writer()
    writer({"type": "web_fetch", "content": f"🌐 正在抓取网页: {url}"})
    print(f"[web_fetch] 请求前端抓取网页 (url={url})")

    # 模拟返回网页内容
    return f"网页内容: 这是从 '{url}' 抓取到的内容..."


@tool
def web_search(query: str) -> str:
    """
    web_search 工具 - 根据查询关键词进行网络搜索

    Args:
        query: 搜索查询关键词

    Returns:
        搜索结果字符串
    """
    # todo
    # 这里可以实现一个简单的网络搜索逻辑，或者直接请求前端进行搜索
    writer = get_stream_writer()
    writer({"type": "web_search", "content": f"🔎 正在进行网络搜索: {query}"})
    print(f"[WebSearch] 请求前端进行网络搜索 (query={query})")

    # 模拟返回搜索结果
    return f"搜索结果: 这是针对 '{query}' 的网络搜索结果..."


# region Tools 注册

ALL_TOOLS = [read_document, generate_document]
TOOL_MAP = {t.name: t for t in ALL_TOOLS}


# region System Prompt

AGENT_PROMPT = """你是专业的文档处理和写作助手。你可以：
1. 润色、重写、翻译、扩写、缩写文档内容
2. 调整格式（字体、字号、对齐、缩进等）
3. 回答用户的问题和进行日常对话

【工具使用规则 - 非常重要】

🔵 **必须调用 read_document 工具的情况：**
只要用户提到"文档"、"文章"、"这篇"、"全文"、"内容"等词，且你没有收到任何文档内容，就**必须立即调用 read_document**！

读取全文传入 startPos=-1, endPos=-1。

具体场景：
- "这是一篇什么文章" → 调用 read_document(-1, -1)
- "这篇文档讲了什么" → 调用 read_document(-1, -1)
- "润色全文" → 调用 read_document(-1, -1)
- "修改第三段" → 调用 read_document(-1, -1)
- "分析一下文档" → 调用 read_document(-1, -1)
- "总结文档内容" → 调用 read_document(-1, -1)
- "检查一下" → 调用 read_document(-1, -1)

⚠️ **关键判断**：如果用户的请求涉及文档/文章，但你没有看到任何文档JSON内容，就调用 read_document！

✅ **调用 generate_document 工具的情况：**
用户**已经提供了文档内容**（你能看到 paragraphs 数据），并且要求修改/润色/生成。
调用 generate_document 后，请用1-2句话简要总结你做了哪些修改。

📋 **格式保持规则（极其重要）：**
调用 generate_document 时，必须**完整保留原文档的 pStyle 和 rStyle**！
- 每个段落的 pStyle（对齐、行距、缩进、段前段后、样式名等）必须与原文档一致
- 每个 run 的 rStyle（字体、字号、粗体、斜体、颜色等）必须与原文档一致
- **只修改文字内容，不改动任何格式属性**，除非用户明确要求修改格式
- 如果用户要求“加粗”、“改字体”等格式操作，只修改对应的格式字段
- 简而言之：**格式原样复制，只改内容**

❌ **不调用任何工具的情况：**
- 纯粹的问候（"你好"）
- 与文档无关的问题（"什么是AI"、"今天天气怎么样"）
- 询问你的功能（"你能干什么"）

【工具调用要求】
调用工具时：
1. 先用1-2句话说明你要做什么
2. 然后**立即调用工具**
"""


# region Create LLM


def create_llm(model_name: str) -> ChatOpenAI:
    """创建 LLM 实例，使用 llm_client 统一管理配置"""
    provider_info = LLMClientManager.get_provider_info(model_name)

    return ChatOpenAI(
        model=model_name,
        openai_api_key=provider_info.api_key,
        openai_api_base=provider_info.base_url,
        temperature=0.7,
        streaming=True,
    )


# region LangGraph Agent（ReAct）


def build_graph(llm_with_tools):
    """
    构建 LangGraph ReAct 工作流（单一智能体）

    流程：
    START -> agent -> (有 tool_calls?) -> tools -> agent -> ... -> END
                   -> (无 tool_calls) -> END

    agent 自动循环调用工具，直到不再需要工具为止。
    """
    graph = StateGraph(MessagesState)

    # ---- 节点 ----

    def agent_node(state: MessagesState) -> dict:
        """单一 Agent 节点 - 决定下一步行动或直接回复"""
        print("[Agent] 开始处理")
        response = llm_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    def tools_node(state: MessagesState) -> dict:
        """工具执行节点 - 执行 Agent 请求的所有工具"""
        last_message = state["messages"][-1]
        results = []

        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            print(f"[Tools] 执行工具: {tool_name}")

            tool_fn = TOOL_MAP.get(tool_name)
            if tool_fn:
                result = tool_fn.invoke(tool_call["args"])
                # 标准化结果为字符串
                if isinstance(result, dict):
                    content = json.dumps(result, ensure_ascii=False)
                elif isinstance(result, str):
                    content = result
                else:
                    content = str(result)
                results.append(ToolMessage(content=content, tool_call_id=tool_call["id"], name=tool_name))
            else:
                print(f"[Tools] ⚠️ 未知工具: {tool_name}")
                results.append(
                    ToolMessage(content=f"错误: 未知工具 {tool_name}", tool_call_id=tool_call["id"], name=tool_name)
                )

        return {"messages": results}

    # ---- 路由 ----

    def should_continue(state: MessagesState) -> str:
        """判断 Agent 是否还需要调用工具"""
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            print("[Router] -> tools")
            return "tools"
        print("[Router] -> END")
        return END

    # ---- 构建图 ----

    graph.add_node("agent", agent_node)
    graph.add_node("tools", tools_node)

    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")  # 工具执行完毕，始终回到 Agent

    return graph.compile()


# region 主处理函数


async def process_writing_request_stream(
    message: str,
    document_range: list[dict] | None = None,
    history: list | None = None,
    model: str | None = None,
    mode: str | None = None,
    session_id: str | None = None,
) -> AsyncGenerator[str, None]:
    """
    使用 LangGraph ReAct Agent 处理写作请求（流式输出）

    Args:
        message: 用户消息
        document_range: 文档范围列表 [{startPos: int, endPos: int}, ...]
        history: 历史消息
        model: 用户选择的模型
        mode: 对话模式（agent/ask）
        session_id: WebSocket 会话 ID（用于工具回调）

    Yields:
        SSE 格式的流式输出
    """
    print("[Agent] 开始处理请求")
    print(f"[Agent] 模式: {mode}")

    model_name = resolve_model(model or "auto")
    llm = create_llm(model_name)

    # 根据模式决定绑定哪些工具
    is_ask_mode = mode == "ask"

    if is_ask_mode:
        tools = [read_document]
        print("[Agent] ask 模式，已绑定 read_document")
    else:
        tools = ALL_TOOLS
        print(f"[Agent] agent 模式，已绑定 {[t.name for t in tools]}")

    llm_with_tools = llm.bind_tools(tools)
    app = build_graph(llm_with_tools)

    try:
        messages = [SystemMessage(content=AGENT_PROMPT)]

        # 构建用户消息
        user_content = message
        if document_range:
            # 有文档范围时，指示 agent 调用 read_document 读取这些范围
            range_instructions = "\n".join(
                f"  - read_document(startPos={r.get('startPos', -1)}, endPos={r.get('endPos', -1)})"
                for r in document_range
            )
            user_content = (
                f"用户要求：{message}\n\n"
                f"⚠️ 请先调用 read_document 工具读取以下文档范围（必须调用，不可跳过）：\n{range_instructions}\n"
                f"读取到文档内容后，根据用户要求进行处理，并调用 generate_document 工具输出结果。"
            )
            print(f"[Agent] 文档范围: {document_range}")

        messages.append(HumanMessage(content=user_content))

        print(f"[Agent] 消息数量: {len(messages)}")

        # 获取事件循环，注册供 tool 使用
        loop = asyncio.get_running_loop()
        if session_id:
            register_loop(session_id, loop)

        # 队列用于线程间传递流式数据
        queue: asyncio.Queue = asyncio.Queue()
        has_tool_result = False

        def run_stream():
            """在独立线程中运行同步的 LangGraph stream"""
            try:
                if session_id:
                    _current_session_id.set(session_id)

                response = app.stream(
                    {"messages": messages},
                    stream_mode=["messages", "custom"],
                )

                for stream_item in response:
                    asyncio.run_coroutine_threadsafe(queue.put(stream_item), loop)

                asyncio.run_coroutine_threadsafe(queue.put(None), loop)
            except Exception as e:
                asyncio.run_coroutine_threadsafe(queue.put(("error", str(e))), loop)

        # 在线程池中启动
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        executor.submit(run_stream)

        # 从队列中消费流式数据
        while True:
            stream_item = await queue.get()

            if stream_item is None:
                break

            if isinstance(stream_item, tuple) and stream_item[0] == "error":
                raise Exception(stream_item[1])

            if not isinstance(stream_item, tuple):
                continue

            input_type, chunk = stream_item

            if input_type == "messages":
                if not chunk or len(chunk) == 0:
                    continue
                msg = chunk[0]
                content = msg.content

                if isinstance(msg, ToolMessage):
                    # 根据工具名称决定是否转发给前端
                    tool_name = getattr(msg, "name", "")

                    if tool_name == "read_document":
                        # read_document 结果是中间数据，不发给前端
                        has_tool_result = True
                        print(f"[Agent] ⏭️ 跳过 read_document 工具返回值")
                        continue

                    if tool_name == "generate_document":
                        # generate_document 结果发给前端渲染
                        try:
                            doc_json = json.loads(content)
                            if "paragraphs" in doc_json:
                                print(f"[Agent] ✅ 提取到 generate_document 结果")
                                yield f"data: {json.dumps({'type': 'json', 'content': doc_json}, ensure_ascii=False)}\n\n"
                                has_tool_result = True
                                continue
                        except json.JSONDecodeError:
                            pass

                    # 其他工具的结果，跳过
                    continue

                # 普通文本输出（Agent 的回复）
                if content:
                    yield f"data: {json.dumps({'type': 'text', 'content': content}, ensure_ascii=False)}\n\n"

            elif input_type == "custom":
                # stream_writer 的输出（工具的状态消息）
                print(f"[Agent] 自定义输出: {chunk}")
                if chunk:
                    if isinstance(chunk, dict):
                        yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                    else:
                        yield f"data: {json.dumps({'type': 'status', 'content': str(chunk)}, ensure_ascii=False)}\n\n"

        # 只在 agent 模式下且期望生成文档时显示警告
        if not has_tool_result and not is_ask_mode and document_range:
            yield f"data: {json.dumps({'type': 'status', 'content': '⚠️ 没有检测到生成文档，模型可能不支持'}, ensure_ascii=False)}\n\n"

        yield "data: [DONE]\n\n"

    except Exception as e:
        print(f"[Agent Error] {e}")
        traceback.print_exc()
        yield f"data: {json.dumps({'type': 'text', 'content': f'错误: {str(e)}'}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
