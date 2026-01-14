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
- content: 润色、优化、改进、重写、改写、扩写、缩写、翻译、格式调整、排版、字体、字号、对齐、缩进
- chat: 普通对话、问答、解释说明"""

CONTENT_PROMPT = """你是专业的文档处理专家，负责润色、重写、翻译、格式调整等所有文档相关任务。

🔴【强制要求 - 必须遵守】🔴
你必须完成以下两步，缺一不可：
第一步：用2-3句话说明你要做什么修改
第二步：调用 generate_document 工具生成完整的文档 JSON

⚠️ 重要：禁止直接输出 JSON 文本！必须通过工具调用返回 JSON！
⚠️ 如果你输出 ```json 代码块，用户将无法看到修改后的文档！
⚠️ 你必须使用 generate_document 函数工具来返回结果！

【格式原则】
- 如果用户只要求改内容：所有格式属性（fontName, fontSize, alignment 等）必须100%原样复制
- 如果用户要求改格式：可以修改格式属性，但文本内容保持不变

【必须原样复制的格式属性】
段落级别：alignment, lineSpacing, indentFirstLine, indentLeft, indentRight, spaceBefore, spaceAfter, styleName
Run级别：fontName, fontSize, bold, italic, underline, color 等

【你可以修改的内容】
- runs 里的 text 字段（文字内容）
- paragraphs 里的 text 字段（段落完整文本）
- 如果用户要求改格式，则可以修改格式属性

【扩写新增段落时】
新段落要沿用相邻段落的完整格式。"""

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
            if task_type not in ["content", "chat"]:
                msg_lower = message.lower()
                # 任何文档相关操作都归类为 content
                if any(kw in msg_lower for kw in ["润色", "优化", "改进", "重写", "改写", "扩写", "缩写", "翻译", "格式", "排版", "字体", "字号", "对齐", "缩进"]):
                    task_type = "content"
                else:
                    task_type = "chat"

            print(f"[Router] 任务类型: {task_type}")

        # ===== Step 2: 选择对应的 Agent 处理 =====
        if task_type == "content":
            async for chunk in process_content_agent(llm, message, document_json, history):
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

    # 强制调用工具 - 使用 "required" 确保必须调用工具
    llm_with_tools = llm.bind_tools(
        [generate_document],
        tool_choice="required"  # OpenAI API 新格式：必须调用工具
    )
    
    print("[ContentAgent] 已设置强制调用工具模式: required")

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

    print(f"[ContentAgent] 消息数量: {len(messages)}")
    print(f"[ContentAgent] 工具已绑定: {llm_with_tools.bound}")

    # 🔥 改用累积方式处理流式工具调用
    # 因为工具参数在流式模式下是逐步传输的，需要完整收集
    text_chunks = []
    tool_call_chunks = []
    
    async for chunk in llm_with_tools.astream(messages):
        # 输出文字内容（打字机效果）
        if chunk.content:
            text_chunks.append(chunk.content)
            print(f"[ContentAgent] 文本块: {chunk.content[:50]}...")
            yield f"data: {json.dumps({'type': 'text', 'content': chunk.content}, ensure_ascii=False)}\n\n"

        # 收集工具调用（流式模式下需要累积）
        if hasattr(chunk, "tool_calls") and chunk.tool_calls:
            for tc in chunk.tool_calls:
                if tc.get("name") == "generate_document":  # 只处理有名称的
                    tool_call_chunks.append(tc)
                    print(f"[ContentAgent] 收集工具调用块: {tc.get('id', 'no-id')}")
    
    # 处理累积的工具调用
    if tool_call_chunks:
        print(f"[ContentAgent] 共收集到 {len(tool_call_chunks)} 个工具调用块")
        # 使用最后一个完整的工具调用（包含完整参数）
        final_tool_call = tool_call_chunks[-1]
        args = final_tool_call.get("args", {})
        
        print(f"[ContentAgent] 最终 args 类型: {type(args)}")
        print(f"[ContentAgent] 最终 args 内容: {json.dumps(args, ensure_ascii=False)[:500]}...")
        
        # 检查参数结构
        document_output = None
        if isinstance(args, dict) and args:  # 确保 args 不为空
            if "paragraphs" in args:
                document_output = args
                print(f"[ContentAgent] ✅ 找到 paragraphs")
            elif "document" in args and isinstance(args["document"], dict):
                document_output = args["document"]
                print(f"[ContentAgent] ✅ 找到 document 字段")
            else:
                print(f"[ContentAgent] ⚠️ args keys: {list(args.keys())}")
        
        if document_output and "paragraphs" in document_output:
            para_count = len(document_output.get("paragraphs", []))
            print(f"[ContentAgent] ✅ 成功生成 {para_count} 个段落")
            yield f"data: {json.dumps({'type': 'json', 'content': document_output}, ensure_ascii=False)}\n\n"
        else:
            print(f"[ContentAgent] ❌ 没有有效的文档输出")
    else:
        print(f"[ContentAgent] ⚠️ 警告：没有收集到工具调用")



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
