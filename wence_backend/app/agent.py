"""
多 Agent 协作系统 - 使用 LangGraph
重构版本：更好的状态管理、可观测性和扩展性
"""

from typing import TypedDict, Annotated, Sequence, Literal, Optional
from typing_extensions import TypedDict
import operator
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel, Field
import json
import asyncio

from app.core.config import settings
from app.services.llm_client import resolve_model


# ============== Pydantic 模型定义（用于 Tool Schema）==============

class Run(BaseModel):
    """格式块 - 一段具有相同格式的文字"""
    text: str = Field(description="文字内容")
    fontName: Optional[str] = Field(None, description="字体名称，如 '宋体', 'Times New Roman'")
    fontSize: Optional[float] = Field(None, description="字号")
    bold: Optional[bool] = Field(None, description="是否加粗")
    italic: Optional[bool] = Field(None, description="是否斜体")
    underline: Optional[str] = Field(None, description="下划线：none/single/double/thick")
    color: Optional[str] = Field(None, description="颜色，如 '#000000'")
    highlight: Optional[str] = Field(None, description="高亮色")
    strikethrough: Optional[bool] = Field(None, description="是否删除线")
    superscript: Optional[bool] = Field(None, description="是否上标")
    subscript: Optional[bool] = Field(None, description="是否下标")


class Paragraph(BaseModel):
    """段落"""
    text: str = Field(description="段落完整文本")
    runs: list[Run] = Field(description="格式块数组，每个 run 是一段具有相同格式的文字")
    alignment: Optional[str] = Field("left", description="对齐方式：left/center/right/justify")
    lineSpacing: Optional[float] = Field(None, description="行间距")
    indentLeft: Optional[float] = Field(None, description="左缩进（磅）")
    indentRight: Optional[float] = Field(None, description="右缩进（磅）")
    indentFirstLine: Optional[float] = Field(None, description="首行缩进（磅）")
    spaceBefore: Optional[float] = Field(None, description="段前间距（磅）")
    spaceAfter: Optional[float] = Field(None, description="段后间距（磅）")
    styleName: Optional[str] = Field(None, description="样式名称，如 '标题 1', '标题 2', '正文'")


class Cell(BaseModel):
    """表格单元格"""
    text: str = Field(description="单元格文本")
    rowSpan: Optional[int] = Field(1, description="跨行数")
    colSpan: Optional[int] = Field(1, description="跨列数")
    alignment: Optional[str] = Field("left", description="水平对齐")
    verticalAlignment: Optional[str] = Field("top", description="垂直对齐")


class Table(BaseModel):
    """表格"""
    rows: int = Field(description="行数")
    columns: int = Field(description="列数")
    cells: list[list[Cell]] = Field(description="单元格二维数组")
    tableAlignment: Optional[str] = Field("left", description="表格对齐：left/center/right")


class DocumentOutput(BaseModel):
    """文档输出结构"""
    paragraphs: list[Paragraph] = Field(description="段落数组")
    tables: Optional[list[Table]] = Field(None, description="表格数组（可选）")


# ============== 状态定义 ==============

class AgentState(TypedDict):
    """Agent 状态"""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    task_type: str  # content, format, chat
    user_request: str
    document_json: dict | None
    history: list | None
    model: str
    mode: str
    streaming_buffer: str  # 用于流式输出
    document_output: dict | None  # 生成的文档 JSON


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
    # 转换 Pydantic 模型为 dict
    return document.model_dump()


# ============== System Prompts ==============

ROUTER_PROMPT = """分析用户请求，返回以下任务类型之一（只返回单词）：
- content: 润色、优化、改进、重写、改写、扩写、缩写、翻译
- format: 格式调整、排版、字体、字号、对齐、缩进
- chat: 普通对话、问答、解释说明"""

CONTENT_PROMPT = """你是专业的文档内容处理专家，负责润色、重写、翻译等任务。

【工作流程 - 必须严格遵守】
第一步：先用2-3句话说明你要做什么修改，帮助用户理解你的思路
例如："我将把实习目的从3点扩写为6点，保持原有格式和语言风格，增加更多细节和具体说明..."

第二步：立即调用 generate_document 工具生成完整的文档 JSON

⚠️ 注意：两步都必须完成！先输出文字说明，再调用工具。

【核心原则】格式属性必须100%复制原值！
除非用户明确说"改格式"、"调整格式"等，否则所有格式属性必须与原文档完全一致。

【必须原样复制的格式属性】
段落级别：alignment, lineSpacing, indentFirstLine, indentLeft, indentRight, spaceBefore, spaceAfter, styleName
Run级别：fontName, fontSize, bold, italic, underline, color 等

【你只能修改的内容】
- runs 里的 text 字段（文字内容）
- paragraphs 里的 text 字段（段落完整文本）

【扩写新增段落时】
新段落要沿用相邻段落的完整格式。"""

FORMAT_PROMPT = """你是文档格式专家，负责调整文档的排版格式。

【工作流程 - 必须严格遵守】
第一步：先用2-3句话说明你要做的格式调整，例如：
"我将把所有段落改为居中对齐，标题设置为黑体加粗，正文字号调整为14号..."

第二步：立即调用 generate_document 工具生成调整后的文档 JSON

⚠️ 注意：两步都必须完成！先输出文字说明，再调用工具。

可调整的格式属性：
- alignment: 对齐方式 (left/center/right/justify)
- runs 中的格式：fontName(字体), fontSize(字号), bold(加粗), italic(斜体), color(颜色)
- styleName: 段落样式

注意：保持文本内容不变，只修改格式属性。"""

CHAT_PROMPT = """你是 AI 写作助手，帮助用户解答问题。
如果用户想修改文档，引导他们使用具体的功能（润色、重写、翻译、格式调整等）。
直接用文字回答，不需要调用工具。"""


# ============== Node 函数 ==============

def router_node(state: AgentState) -> AgentState:
    """路由节点：判断任务类型"""
    mode = state.get("mode", "agent")
    
    # 如果是 ask 模式，直接使用 chat
    if mode == "ask":
        print(f"[Router] Ask 模式，使用 chat")
        return {**state, "task_type": "chat"}
    
    # 创建 LLM
    model_name = resolve_model(state["model"])
    llm = _create_llm(model_name)
    
    # 调用路由
    messages = [
        SystemMessage(content=ROUTER_PROMPT),
        HumanMessage(content=state["user_request"])
    ]
    
    response = llm.invoke(messages)
    task_type = response.content.strip().lower()
    
    # 验证并修正任务类型
    if task_type not in ["content", "format", "chat"]:
        msg_lower = state["user_request"].lower()
        if any(kw in msg_lower for kw in ["润色", "优化", "改进", "重写", "改写", "扩写", "缩写", "翻译"]):
            task_type = "content"
        elif any(kw in msg_lower for kw in ["格式", "排版", "字体", "字号", "对齐"]):
            task_type = "format"
        else:
            task_type = "chat"
    
    print(f"[Router] 任务类型: {task_type}")
    return {**state, "task_type": task_type}


def content_agent_node(state: AgentState) -> AgentState:
    """内容处理 Agent"""
    print(f"[ContentAgent] 开始处理")
    
    model_name = resolve_model(state["model"])
    llm = _create_llm(model_name)
    # 绑定工具，让 LLM 自然决定何时调用（先输出说明，再调用工具）
    llm_with_tools = llm.bind_tools([generate_document])
    
    # 构建消息
    messages = [SystemMessage(content=CONTENT_PROMPT)]
    
    # 添加历史
    for msg in (state.get("history") or [])[-6:]:
        if isinstance(msg, dict) and "role" in msg and "content" in msg:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                messages.append(AIMessage(content=msg["content"]))
    
    # 构建用户消息
    user_content = state["user_request"]
    if state.get("document_json"):
        doc_json = state["document_json"]
        simplified = {
            "text": doc_json.get("text", ""),
            "paragraphs": []
        }
        for para in doc_json.get("paragraphs", []):
            simplified["paragraphs"].append({
                "text": para.get("text", ""),
                "alignment": para.get("alignment", "left"),
                "lineSpacing": para.get("lineSpacing"),
                "indentLeft": para.get("indentLeft"),
                "indentRight": para.get("indentRight"),
                "indentFirstLine": para.get("indentFirstLine"),
                "spaceBefore": para.get("spaceBefore"),
                "spaceAfter": para.get("spaceAfter"),
                "styleName": para.get("styleName", ""),
                "runs": para.get("runs", [])
            })
        if doc_json.get("tables"):
            simplified["tables"] = doc_json["tables"]
        
        user_content = f"文档结构（格式属性必须原样复制）：\n```json\n{json.dumps(simplified, ensure_ascii=False, indent=2)}\n```\n\n用户要求：{state['user_request']}"
    
    messages.append(HumanMessage(content=user_content))
    
    # 调用 LLM
    response = llm_with_tools.invoke(messages)
    
    # 调试：打印完整响应
    print(f"[ContentAgent] Response type: {type(response)}")
    print(f"[ContentAgent] Response content: {response.content[:200] if response.content else 'None'}")
    print(f"[ContentAgent] Has tool_calls: {bool(response.tool_calls)}")
    if response.tool_calls:
        print(f"[ContentAgent] Tool calls count: {len(response.tool_calls)}")
        for i, tc in enumerate(response.tool_calls):
            print(f"[ContentAgent] Tool call {i}: name={tc.get('name')}, args keys={list(tc.get('args', {}).keys())}")
    
    # 处理工具调用
    document_output = None
    if response.tool_calls:
        for tool_call in response.tool_calls:
            if tool_call["name"] == "generate_document":
                args = tool_call["args"]
                print(f"[ContentAgent] Tool args: {json.dumps(args, ensure_ascii=False)[:500]}")
                
                # 检查参数结构
                if isinstance(args, dict):
                    # 如果 args 直接包含 paragraphs
                    if "paragraphs" in args:
                        document_output = args
                    # 如果 args 包含 document 对象
                    elif "document" in args:
                        document_output = args["document"]
                    else:
                        print(f"[ContentAgent Error] Unexpected args structure: {list(args.keys())}")
                        document_output = args
                
                if document_output:
                    para_count = len(document_output.get('paragraphs', []))
                    print(f"[ContentAgent] 生成了 {para_count} 段落")
                else:
                    print(f"[ContentAgent Error] document_output is None")
    
    # LLM 会自然输出说明文字，直接使用
    return {
        **state,
        "streaming_buffer": response.content or "",
        "document_output": document_output
    }


def format_agent_node(state: AgentState) -> AgentState:
    """格式处理 Agent"""
    print(f"[FormatAgent] 开始处理")
    
    model_name = resolve_model(state["model"])
    llm = _create_llm(model_name)
    # 绑定工具，让 LLM 自然决定何时调用（先输出说明，再调用工具）
    llm_with_tools = llm.bind_tools([generate_document])
    
    # 构建消息（类似 content_agent_node）
    messages = [SystemMessage(content=FORMAT_PROMPT)]
    
    for msg in (state.get("history") or [])[-6:]:
        if isinstance(msg, dict) and "role" in msg and "content" in msg:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                messages.append(AIMessage(content=msg["content"]))
    
    user_content = state["user_request"]
    if state.get("document_json"):
        doc_json = state["document_json"]
        simplified = {
            "text": doc_json.get("text", ""),
            "paragraphs": [
                {
                    "text": para.get("text", ""),
                    "alignment": para.get("alignment", "left"),
                    "lineSpacing": para.get("lineSpacing"),
                    "indentLeft": para.get("indentLeft"),
                    "indentRight": para.get("indentRight"),
                    "indentFirstLine": para.get("indentFirstLine"),
                    "spaceBefore": para.get("spaceBefore"),
                    "spaceAfter": para.get("spaceAfter"),
                    "styleName": para.get("styleName", ""),
                    "runs": para.get("runs", [])
                }
                for para in doc_json.get("paragraphs", [])
            ]
        }
        user_content = f"文档结构：\n```json\n{json.dumps(simplified, ensure_ascii=False, indent=2)}\n```\n\n用户要求：{state['user_request']}"
    
    messages.append(HumanMessage(content=user_content))
    
    response = llm_with_tools.invoke(messages)
    
    # 调试：打印响应
    print(f"[FormatAgent] Response content: {response.content[:200] if response.content else 'None'}")
    print(f"[FormatAgent] Has tool_calls: {bool(response.tool_calls)}")
    
    document_output = None
    if response.tool_calls:
        for tool_call in response.tool_calls:
            if tool_call["name"] == "generate_document":
                args = tool_call["args"]
                
                # 检查参数结构
                if isinstance(args, dict):
                    if "paragraphs" in args:
                        document_output = args
                    elif "document" in args:
                        document_output = args["document"]
                    else:
                        document_output = args
                
                if document_output:
                    para_count = len(document_output.get('paragraphs', []))
                    print(f"[FormatAgent] 生成了 {para_count} 段落")
    
    # LLM 会自然输出说明文字，直接使用
    return {
        **state,
        "streaming_buffer": response.content or "",
        "document_output": document_output
    }


def chat_agent_node(state: AgentState) -> AgentState:
    """聊天 Agent"""
    print(f"[ChatAgent] 开始处理")
    
    model_name = resolve_model(state["model"])
    llm = _create_llm(model_name)
    
    messages = [SystemMessage(content=CHAT_PROMPT)]
    
    for msg in (state.get("history") or [])[-6:]:
        if isinstance(msg, dict) and "role" in msg and "content" in msg:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                messages.append(AIMessage(content=msg["content"]))
    
    user_content = state["user_request"]
    if state.get("document_json"):
        doc_text = state["document_json"].get("text", "")
        if doc_text:
            user_content = f"文档内容：\n{doc_text[:1000]}\n\n用户问题：{state['user_request']}"  # 注意这个长度限制，避免过长的输入导致模型崩溃
                                                                                               # 后期考虑增加分段输入或者摘要输入的功能
    
    messages.append(HumanMessage(content=user_content))
    
    response = llm.invoke(messages)
    
    return {
        **state,
        "streaming_buffer": response.content,
        "document_output": None
    }


def route_by_task(state: AgentState) -> Literal["content_agent", "format_agent", "chat_agent"]:
    """根据任务类型路由到不同的 agent"""
    task_type = state.get("task_type", "chat")
    if task_type == "content":
        return "content_agent"
    elif task_type == "format":
        return "format_agent"
    else:
        return "chat_agent"


def _create_llm(model_name: str):
    """创建 LLM 实例"""

    # 默认使用 OpenAI 兼容接口
    return ChatOpenAI(
        model=model_name,
        openai_api_key=settings.OPENAI_API_KEY,
        openai_api_base=settings.OPENAI_BASE_URL,
        temperature=0.7,
        streaming=True  # 🔥 关键：启用流式输出
    )


# ============== 创建 Graph ==============

def create_agent_graph():
    """创建 Agent 工作流图"""
    workflow = StateGraph(AgentState)
    
    # 添加节点
    workflow.add_node("router", router_node)
    workflow.add_node("content_agent", content_agent_node)
    workflow.add_node("format_agent", format_agent_node)
    workflow.add_node("chat_agent", chat_agent_node)
    
    # 设置入口点
    workflow.set_entry_point("router")
    
    # 添加条件边
    workflow.add_conditional_edges(
        "router",
        route_by_task,
        {
            "content_agent": "content_agent",
            "format_agent": "format_agent",
            "chat_agent": "chat_agent"
        }
    )
    
    # 所有 agent 完成后结束
    workflow.add_edge("content_agent", END)
    workflow.add_edge("format_agent", END)
    workflow.add_edge("chat_agent", END)
    
    return workflow.compile()


# ============== 主处理函数 ==============

async def process_writing_request_langgraph(
    message: str,
    document_json: dict | None = None,
    history: list | None = None,
    model: str | None = None,
    mode: str | None = None
):
    """
    使用 LangGraph 处理写作请求
    
    Args:
        message: 用户消息
        document_json: 用户选中的文档 JSON
        history: 历史消息
        model: 用户选择的模型
        mode: 对话模式（agent/ask）
    
    Yields:
        SSE 格式的流式输出
    """
    print(f"[LangGraph] 开始处理请求")
    print(f"[LangGraph] 模式: {mode}")
    
    # 创建 graph
    app = create_agent_graph()
    
    # 初始状态
    initial_state = {
        "messages": [],
        "task_type": "",
        "user_request": message,
        "document_json": document_json,
        "history": history,
        "model": model or "auto",
        "mode": mode or "agent",
        "streaming_buffer": "",
        "document_output": None
    }
    
    try:
        # 运行 graph
        result = await app.ainvoke(initial_state)
        
        # 输出文字说明
        if result.get("streaming_buffer"):
            yield f"data: {json.dumps({'type': 'text', 'content': result['streaming_buffer']}, ensure_ascii=False)}\n\n"
        
        # 输出文档 JSON
        if result.get("document_output"):
            yield f"data: {json.dumps({'type': 'json', 'content': result['document_output']}, ensure_ascii=False)}\n\n"
        
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        print(f"[LangGraph Error] {e}")
        import traceback
        traceback.print_exc()
        yield f"data: {json.dumps({'type': 'text', 'content': f'错误: {str(e)}'}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"


# ============== 流式版本（使用 astream_events）==============

async def process_writing_request_stream(
    message: str,
    document_json: dict | None = None,
    history: list | None = None,
    model: str | None = None,
    mode: str | None = None
):
    """
    使用 LangGraph 处理写作请求（流式版本，实时输出 token）
    
    使用 astream_events() API 获取 LLM 的实时 token 流
    """
    print(f"[LangGraph Stream] 开始处理请求")
    
    app = create_agent_graph()
    
    initial_state = {
        "messages": [],
        "task_type": "",
        "user_request": message,
        "document_json": document_json,
        "history": history,
        "model": model or "auto",
        "mode": mode or "agent",
        "streaming_buffer": "",
        "document_output": None
    }
    
    try:
        # 使用 astream_events 获取实时 token 流（v2 API）
        accumulated_text = ""
        final_document_output = None
        
        async for event in app.astream_events(initial_state, version="v2"):
            event_type = event.get("event")
            event_name = event.get("name", "")
            
            # 打印所有事件（调试用）
            print(f"[Event] {event_type} | name={event_name}")
            
            # 捕获 LLM 流式输出的每个 token
            if event_type == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    # 实时输出每个 token
                    accumulated_text += chunk.content
                    yield f"data: {json.dumps({'type': 'text', 'content': chunk.content}, ensure_ascii=False)}\n\n"
            
            # 捕获工具调用结束
            elif event_type == "on_tool_end":
                tool_name = event.get("name")
                if tool_name == "generate_document":
                    output = event.get("data", {}).get("output")
                    if output:
                        final_document_output = output
                        print(f"[Stream] 捕获到工具输出，段落数: {len(output.get('paragraphs', []))}")
            
            # 捕获节点完成
            elif event_type == "on_chain_end":
                chain_name = event.get("name")
                output = event.get("data", {}).get("output")
                
                # 调试：打印完整 output 结构
                if chain_name in ["content_agent", "format_agent", "chat_agent"]:
                    print(f"[Stream] {chain_name} 结束，output keys: {list(output.keys()) if isinstance(output, dict) else type(output)}")
                
                # 处理 content_agent 和 format_agent
                if chain_name in ["content_agent", "format_agent"]:
                    if output and isinstance(output, dict):
                        # 输出文字说明
                        if output.get("streaming_buffer"):
                            text = output["streaming_buffer"]
                            yield f"data: {json.dumps({'type': 'text', 'content': text}, ensure_ascii=False)}\n\n"
                            print(f"[Stream] 输出文字: {text[:50]}...")
                        
                        # 保存 document_output
                        if output.get("document_output"):
                            final_document_output = output["document_output"]
                            print(f"[Stream] 捕获文档输出")
                
                # 处理 chat_agent
                elif chain_name == "chat_agent":
                    if output and isinstance(output, dict):
                        if output.get("streaming_buffer"):
                            text = output["streaming_buffer"]
                            yield f"data: {json.dumps({'type': 'text', 'content': text}, ensure_ascii=False)}\n\n"
                            print(f"[Stream] Chat 输出: {text[:50]}...")
        
        # 输出最终的文档 JSON
        if final_document_output:
            yield f"data: {json.dumps({'type': 'json', 'content': final_document_output}, ensure_ascii=False)}\n\n"
        
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        print(f"[LangGraph Error] {e}")
        import traceback
        traceback.print_exc()
        yield f"data: {json.dumps({'type': 'text', 'content': f'错误: {str(e)}'}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
