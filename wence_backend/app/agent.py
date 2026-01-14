"""
多 Agent 协作系统 - 使用纯 LangChain（无 LangGraph）
优势：完美的流式输出 + 简单清晰的代码结构
"""

import json
from collections.abc import AsyncGenerator

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.services.llm_client import LLMClientManager, resolve_model

# ============== Pydantic 模型定义（用于 Tool Schema）==============


class Run(BaseModel):
    """格式块 - 一段具有相同格式的文字"""

    text: str = Field(description="文字内容")
    fontName: str | None = Field(None, description="字体名称，如 '宋体', 'Times New Roman'")
    fontSize: float | None = Field(None, description="字号")
    bold: bool | None = Field(None, description="是否加粗")
    italic: bool | None = Field(None, description="是否斜体")
    underline: str | None = Field(None, description="下划线：none/single/double/thick")
    color: str | None = Field(None, description="颜色，如 '#000000'")
    highlight: str | None = Field(None, description="高亮色")
    strikethrough: bool | None = Field(None, description="是否删除线")
    superscript: bool | None = Field(None, description="是否上标")
    subscript: bool | None = Field(None, description="是否下标")


class Paragraph(BaseModel):
    """段落"""

    text: str = Field(description="段落完整文本")
    runs: list[Run] = Field(description="格式块数组，每个 run 是一段具有相同格式的文字")
    alignment: str | None = Field("left", description="对齐方式：left/center/right/justify")
    lineSpacing: float | None = Field(None, description="行间距")
    indentLeft: float | None = Field(None, description="左缩进（磅）")
    indentRight: float | None = Field(None, description="右缩进（磅）")
    indentFirstLine: float | None = Field(None, description="首行缩进（磅）")
    spaceBefore: float | None = Field(None, description="段前间距（磅）")
    spaceAfter: float | None = Field(None, description="段后间距（磅）")
    styleName: str | None = Field(None, description="样式名称，如 '标题 1', '标题 2', '正文'")


class Cell(BaseModel):
    """表格单元格"""

    text: str = Field(description="单元格文本")
    rowSpan: int | None = Field(1, description="跨行数")
    colSpan: int | None = Field(1, description="跨列数")
    alignment: str | None = Field("left", description="水平对齐")
    verticalAlignment: str | None = Field("top", description="垂直对齐")


class Table(BaseModel):
    """表格"""

    rows: int = Field(description="行数")
    columns: int = Field(description="列数")
    cells: list[list[Cell]] = Field(description="单元格二维数组")
    tableAlignment: str | None = Field("left", description="表格对齐：left/center/right")


class DocumentOutput(BaseModel):
    """文档输出结构"""

    paragraphs: list[Paragraph] = Field(description="段落数组")
    tables: list[Table] | None = Field(None, description="表格数组（可选）")


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


# ============== 创建 LLM 实例 ==============


def create_llm(model_name: str) -> ChatOpenAI:
    """创建 LLM 实例，使用 llm_client 统一管理配置"""
    # 获取模型对应的提供商信息
    provider_info = LLMClientManager.get_provider_info(model_name)

    return ChatOpenAI(
        model=model_name,
        openai_api_key=provider_info.api_key,
        openai_api_base=provider_info.base_url,
        temperature=0.7,
    )


# ============== 主处理函数 ==============


async def process_writing_request_stream(
    message: str,
    document_json: dict | None = None,
    history: list | None = None,
    model: str | None = None,
    mode: str | None = None,
) -> AsyncGenerator[str, None]:
    """
    使用纯 LangChain 处理写作请求（流式输出）

    Args:
        message: 用户消息
        document_json: 用户选中的文档 JSON
        history: 历史消息
        model: 用户选择的模型
        mode: 对话模式（agent/ask）

    Yields:
        SSE 格式的流式输出
    """
    print("[LangChain Agent] 开始处理请求")
    print(f"[LangChain Agent] 模式: {mode}")

    model_name = resolve_model(model or "auto")
    llm = create_llm(model_name)

    try:
        # ===== Step 1: 意图识别（Router）=====
        if mode == "ask":
            task_type = "chat"
            print("[Router] Ask 模式，强制使用 chat agent")
        else:
            messages = [SystemMessage(content=ROUTER_PROMPT), HumanMessage(content=message)]

            response = await llm.ainvoke(messages)
            task_type = response.content.strip().lower()

            # 验证并修正任务类型
            if task_type not in ["content", "format", "chat"]:
                msg_lower = message.lower()
                if any(kw in msg_lower for kw in ["润色", "优化", "改进", "重写", "改写", "扩写", "缩写", "翻译"]):
                    task_type = "content"
                elif any(kw in msg_lower for kw in ["格式", "排版", "字体", "字号", "对齐"]):
                    task_type = "format"
                else:
                    task_type = "chat"

            print(f"[Router] 任务类型: {task_type}")

        # ===== Step 2: 选择对应的 Agent 处理 =====
        if task_type == "content":
            async for chunk in process_content_agent(llm, message, document_json, history):
                yield chunk
        elif task_type == "format":
            async for chunk in process_format_agent(llm, message, document_json, history):
                yield chunk
        else:
            async for chunk in process_chat_agent(llm, message, document_json, history):
                yield chunk

        yield "data: [DONE]\n\n"

    except Exception as e:
        print(f"[LangChain Error] {e}")
        import traceback

        traceback.print_exc()
        yield f"data: {json.dumps({'type': 'text', 'content': f'错误: {str(e)}'}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"


# ============== Content Agent ==============


async def process_content_agent(
    llm: ChatOpenAI, message: str, document_json: dict | None, history: list | None
) -> AsyncGenerator[str, None]:
    """内容处理 Agent（流式）"""
    print("[ContentAgent] 开始处理")

    llm_with_tools = llm.bind_tools([generate_document])

    # 构建消息
    messages = [SystemMessage(content=CONTENT_PROMPT)]

    # 添加历史
    for msg in (history or [])[-6:]:
        if isinstance(msg, dict) and "role" in msg and "content" in msg:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                messages.append(AIMessage(content=msg["content"]))

    # 构建用户消息
    user_content = message
    if document_json:
        simplified = {"text": document_json.get("text", ""), "paragraphs": []}
        for para in document_json.get("paragraphs", []):
            simplified["paragraphs"].append(
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
                    "runs": para.get("runs", []),
                }
            )
        if document_json.get("tables"):
            simplified["tables"] = document_json["tables"]

        user_content = f"文档结构（格式属性必须原样复制）：\n```json\n{json.dumps(simplified, ensure_ascii=False, indent=2)}\n```\n\n用户要求：{message}"

    messages.append(HumanMessage(content=user_content))

    # 🔥 流式调用 LLM
    async for chunk in llm_with_tools.astream(messages):
        # 输出文字内容（打字机效果）
        if chunk.content:
            yield f"data: {json.dumps({'type': 'text', 'content': chunk.content}, ensure_ascii=False)}\n\n"

        # 处理工具调用
        if hasattr(chunk, "tool_calls") and chunk.tool_calls:
            for tool_call in chunk.tool_calls:
                if tool_call.get("name") == "generate_document":
                    args = tool_call.get("args", {})

                    # 检查参数结构
                    document_output = None
                    if isinstance(args, dict):
                        if "paragraphs" in args:
                            document_output = args
                        elif "document" in args:
                            document_output = args["document"]
                        else:
                            document_output = args

                    if document_output:
                        para_count = len(document_output.get("paragraphs", []))
                        print(f"[ContentAgent] 生成了 {para_count} 段落")
                        yield f"data: {json.dumps({'type': 'json', 'content': document_output}, ensure_ascii=False)}\n\n"


# ============== Format Agent ==============


async def process_format_agent(
    llm: ChatOpenAI, message: str, document_json: dict | None, history: list | None
) -> AsyncGenerator[str, None]:
    """格式处理 Agent（流式）"""
    print("[FormatAgent] 开始处理")

    llm_with_tools = llm.bind_tools([generate_document])

    # 构建消息（类似 Content Agent）
    messages = [SystemMessage(content=FORMAT_PROMPT)]

    for msg in (history or [])[-6:]:
        if isinstance(msg, dict) and "role" in msg and "content" in msg:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                messages.append(AIMessage(content=msg["content"]))

    user_content = message
    if document_json:
        simplified = {
            "text": document_json.get("text", ""),
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
                    "runs": para.get("runs", []),
                }
                for para in document_json.get("paragraphs", [])
            ],
        }
        user_content = (
            f"文档结构：\n```json\n{json.dumps(simplified, ensure_ascii=False, indent=2)}\n```\n\n用户要求：{message}"
        )

    messages.append(HumanMessage(content=user_content))

    # 🔥 流式调用 LLM
    async for chunk in llm_with_tools.astream(messages):
        if chunk.content:
            yield f"data: {json.dumps({'type': 'text', 'content': chunk.content}, ensure_ascii=False)}\n\n"

        if hasattr(chunk, "tool_calls") and chunk.tool_calls:
            for tool_call in chunk.tool_calls:
                if tool_call.get("name") == "generate_document":
                    args = tool_call.get("args", {})
                    document_output = None
                    if isinstance(args, dict):
                        if "paragraphs" in args:
                            document_output = args
                        elif "document" in args:
                            document_output = args["document"]
                        else:
                            document_output = args

                    if document_output:
                        para_count = len(document_output.get("paragraphs", []))
                        print(f"[FormatAgent] 生成了 {para_count} 段落")
                        yield f"data: {json.dumps({'type': 'json', 'content': document_output}, ensure_ascii=False)}\n\n"


# ============== Chat Agent ==============


async def process_chat_agent(
    llm: ChatOpenAI, message: str, document_json: dict | None, history: list | None
) -> AsyncGenerator[str, None]:
    """聊天 Agent（流式）"""
    print("[ChatAgent] 开始处理")

    messages = [SystemMessage(content=CHAT_PROMPT)]

    for msg in (history or [])[-6:]:
        if isinstance(msg, dict) and "role" in msg and "content" in msg:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                messages.append(AIMessage(content=msg["content"]))

    user_content = message
    if document_json:
        doc_text = document_json.get("text", "")
        if doc_text:
            user_content = f"文档内容：\n{doc_text[:1000]}\n\n用户问题：{message}"

    messages.append(HumanMessage(content=user_content))

    # 🔥 流式调用 LLM（打字机效果）
    async for chunk in llm.astream(messages):
        if chunk.content:
            yield f"data: {json.dumps({'type': 'text', 'content': chunk.content}, ensure_ascii=False)}\n\n"
