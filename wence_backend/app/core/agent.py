"""
多 Agent 协作系统
基于 LangGraph 实现文档处理的多 Agent 协作
"""

from typing import TypedDict, Literal, AsyncGenerator
import json
from langchain_openai import ChatOpenAI
from langchain.tools import tool
from langgraph.graph import StateGraph, START, END
from app.core.config import settings


# ============== 初始化模型 ==============

def get_model(temperature: float = 0.7):
    """获取 LLM 模型实例"""
    return ChatOpenAI(
        model=settings.DEFAULT_MODEL,
        temperature=temperature,
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL if settings.OPENAI_BASE_URL else None
    )


# ============== 定义状态 ==============

class WritingState(TypedDict):
    """写作任务状态"""
    user_message: str           # 用户原始消息
    document_json: dict | None  # 文档 JSON 数据
    task_type: str              # 任务类型: polish/rewrite/translate/format/chat
    history: list               # 历史消息
    result: str                 # 最终结果
    modified_json: dict | None  # 修改后的 JSON（如果需要）


# ============== 定义工具 ==============

@tool
def extract_text_from_json(doc_json: str) -> str:
    """从文档 JSON 中提取纯文本内容
    
    Args:
        doc_json: 文档的 JSON 字符串
    """
    try:
        data = json.loads(doc_json) if isinstance(doc_json, str) else doc_json
        return data.get("text", "")
    except:
        return ""


@tool
def count_paragraphs(doc_json: str) -> int:
    """统计文档中的段落数量
    
    Args:
        doc_json: 文档的 JSON 字符串
    """
    try:
        data = json.loads(doc_json) if isinstance(doc_json, str) else doc_json
        return len(data.get("paragraphs", []))
    except:
        return 0


# ============== Agent 节点定义 ==============

def router_agent(state: WritingState) -> WritingState:
    """
    路由 Agent：分析用户意图，决定任务类型
    """
    model = get_model(temperature=0)
    user_message = state["user_message"].lower()
    
    # 使用 LLM 判断意图
    response = model.invoke([
        {
            "role": "system", 
            "content": """你是一个意图分析助手。分析用户请求，返回以下任务类型之一：
- polish: 润色、优化、改进文字
- rewrite: 重写、改写、扩写、缩写
- translate: 翻译（中英互译等）
- format: 格式调整、排版
- chat: 普通对话、问答

只返回任务类型单词，不要其他内容。"""
        },
        {"role": "user", "content": state["user_message"]}
    ])
    
    task_type = response.content.strip().lower()
    
    # 验证任务类型
    valid_types = ["polish", "rewrite", "translate", "format", "chat"]
    if task_type not in valid_types:
        # 使用关键词匹配作为后备
        if any(kw in user_message for kw in ["润色", "优化", "改进", "改善"]):
            task_type = "polish"
        elif any(kw in user_message for kw in ["重写", "改写", "扩写", "缩写"]):
            task_type = "rewrite"
        elif any(kw in user_message for kw in ["翻译", "translate", "英文", "中文"]):
            task_type = "translate"
        elif any(kw in user_message for kw in ["格式", "排版", "对齐", "缩进"]):
            task_type = "format"
        else:
            task_type = "chat"
    
    print(f"[Router] 识别任务类型: {task_type}")
    return {**state, "task_type": task_type}


def polish_agent(state: WritingState) -> WritingState:
    """
    润色 Agent：专门负责文字润色和优化
    """
    model = get_model(temperature=0.7)
    
    doc_content = ""
    if state["document_json"]:
        doc_content = state["document_json"].get("text", "")
    
    system_prompt = """你是专业的文字润色专家。你的任务是：
1. 保持原文的核心意思不变
2. 让文字更加流畅、优美
3. 修正语法错误和用词不当
4. 提升文章的可读性

如果用户提供了文档内容，请直接返回润色后的文本。
如果没有文档内容，请告诉用户需要选中文档内容。"""

    messages = [{"role": "system", "content": system_prompt}]
    
    if doc_content:
        messages.append({
            "role": "user", 
            "content": f"请润色以下内容：\n\n{doc_content}\n\n用户要求：{state['user_message']}"
        })
    else:
        messages.append({"role": "user", "content": state["user_message"]})
    
    response = model.invoke(messages)
    
    print(f"[Polish Agent] 完成润色")
    return {**state, "result": response.content}


def rewrite_agent(state: WritingState) -> WritingState:
    """
    重写 Agent：专门负责内容重写、改写、扩写、缩写
    """
    model = get_model(temperature=0.8)
    
    doc_content = ""
    if state["document_json"]:
        doc_content = state["document_json"].get("text", "")
    
    system_prompt = """你是专业的内容重写专家。你的任务是：
1. 根据用户要求重新组织和改写内容
2. 如果是扩写，添加更多细节和内容
3. 如果是缩写，精简内容保留核心
4. 保持内容的准确性和连贯性

直接返回重写后的文本。"""

    messages = [{"role": "system", "content": system_prompt}]
    
    if doc_content:
        messages.append({
            "role": "user", 
            "content": f"原文内容：\n\n{doc_content}\n\n用户要求：{state['user_message']}"
        })
    else:
        messages.append({"role": "user", "content": state["user_message"]})
    
    response = model.invoke(messages)
    
    print(f"[Rewrite Agent] 完成重写")
    return {**state, "result": response.content}


def translate_agent(state: WritingState) -> WritingState:
    """
    翻译 Agent：专门负责中英文翻译
    """
    model = get_model(temperature=0.3)  # 翻译用较低温度保证准确性
    
    doc_content = ""
    if state["document_json"]:
        doc_content = state["document_json"].get("text", "")
    
    system_prompt = """你是专业的翻译专家，精通中英文互译。你的任务是：
1. 准确翻译内容，保持原意
2. 翻译要自然流畅，符合目标语言习惯
3. 专业术语翻译准确
4. 自动检测源语言，翻译成另一种语言（中文↔英文）

直接返回翻译结果。"""

    messages = [{"role": "system", "content": system_prompt}]
    
    if doc_content:
        messages.append({
            "role": "user", 
            "content": f"请翻译以下内容：\n\n{doc_content}\n\n用户补充要求：{state['user_message']}"
        })
    else:
        messages.append({"role": "user", "content": state["user_message"]})
    
    response = model.invoke(messages)
    
    print(f"[Translate Agent] 完成翻译")
    return {**state, "result": response.content}


def format_agent(state: WritingState) -> WritingState:
    """
    格式化 Agent：处理文档格式调整
    返回格式建议或修改后的 JSON
    """
    model = get_model(temperature=0.5)
    
    doc_json = state["document_json"]
    
    system_prompt = """你是文档格式专家。你的任务是：
1. 分析用户的格式调整需求
2. 给出具体的格式建议
3. 如果可能，提供修改后的格式参数

文档 JSON 结构说明：
- paragraphs: 段落数组，包含 alignment(对齐)、lineSpacing(行距)、indentFirstLine(首行缩进) 等
- tables: 表格数组
- runs: 格式块，包含 fontName(字体)、fontSize(字号)、bold(加粗)、italic(斜体) 等

请根据用户需求给出格式调整建议。"""

    messages = [{"role": "system", "content": system_prompt}]
    
    if doc_json:
        messages.append({
            "role": "user", 
            "content": f"文档结构：\n```json\n{json.dumps(doc_json, ensure_ascii=False, indent=2)}\n```\n\n用户要求：{state['user_message']}"
        })
    else:
        messages.append({
            "role": "user", 
            "content": f"用户要求：{state['user_message']}\n\n请告诉用户需要先选中文档内容。"
        })
    
    response = model.invoke(messages)
    
    print(f"[Format Agent] 完成格式分析")
    return {**state, "result": response.content}


def chat_agent(state: WritingState) -> WritingState:
    """
    通用聊天 Agent：处理普通对话和问答
    """
    model = get_model(temperature=0.7)
    
    system_prompt = """你是一个专业的AI写作助手，可以帮助用户：
1. 回答关于写作的问题
2. 提供写作建议和技巧
3. 解答文档编辑相关问题
4. 进行友好的对话

如果用户的问题涉及文档操作，请引导用户使用具体功能（润色、重写、翻译、格式调整等）。"""

    messages = [{"role": "system", "content": system_prompt}]
    
    # 添加历史消息
    for msg in state.get("history", [])[-10:]:
        if isinstance(msg, dict) and "role" in msg and "content" in msg:
            messages.append({"role": msg["role"], "content": msg["content"]})
    
    # 添加当前消息
    user_content = state["user_message"]
    if state["document_json"]:
        doc_text = state["document_json"].get("text", "")
        if doc_text:
            user_content = f"[用户选中的文档内容：{doc_text[:500]}{'...' if len(doc_text) > 500 else ''}]\n\n{state['user_message']}"
    
    messages.append({"role": "user", "content": user_content})
    
    response = model.invoke(messages)
    
    print(f"[Chat Agent] 完成对话")
    return {**state, "result": response.content}


# ============== 路由函数 ==============

def route_by_task(state: WritingState) -> Literal["polish", "rewrite", "translate", "format", "chat"]:
    """根据任务类型路由到对应 Agent"""
    return state["task_type"]


# ============== 构建 LangGraph ==============

def build_writing_graph():
    """构建写作助手的 LangGraph"""
    graph = StateGraph(WritingState)
    
    # 添加节点
    graph.add_node("router", router_agent)
    graph.add_node("polish", polish_agent)
    graph.add_node("rewrite", rewrite_agent)
    graph.add_node("translate", translate_agent)
    graph.add_node("format", format_agent)
    graph.add_node("chat", chat_agent)
    
    # 添加边
    graph.add_edge(START, "router")
    graph.add_conditional_edges("router", route_by_task, {
        "polish": "polish",
        "rewrite": "rewrite",
        "translate": "translate",
        "format": "format",
        "chat": "chat"
    })
    
    # 所有 Agent 完成后结束
    graph.add_edge("polish", END)
    graph.add_edge("rewrite", END)
    graph.add_edge("translate", END)
    graph.add_edge("format", END)
    graph.add_edge("chat", END)
    
    return graph.compile()


# 编译图（单例）
writing_app = build_writing_graph()


# ============== 对外接口 ==============

def process_writing_request(
    message: str,
    document_json: dict | None = None,
    history: list | None = None
) -> str:
    """
    处理写作请求（同步版本）
    
    Args:
        message: 用户消息
        document_json: 文档 JSON 数据
        history: 历史消息列表
        
    Returns:
        处理结果文本
    """
    initial_state = WritingState(
        user_message=message,
        document_json=document_json,
        task_type="",
        history=history or [],
        result="",
        modified_json=None
    )
    
    result = writing_app.invoke(initial_state)
    return result["result"]


async def process_writing_request_stream(
    message: str,
    document_json: dict | None = None,
    history: list | None = None
) -> AsyncGenerator[str, None]:
    """
    处理写作请求（流式版本）
    
    Args:
        message: 用户消息
        document_json: 文档 JSON 数据
        history: 历史消息列表
        
    Yields:
        SSE 格式的响应数据
    """
    try:
        # 使用 LLM 进行意图识别
        from openai import AsyncOpenAI
        
        client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL if settings.OPENAI_BASE_URL else None
        )
        
        # 意图识别（非流式，快速调用）
        intent_response = await client.chat.completions.create(
            model=settings.DEFAULT_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": """分析用户请求，返回以下任务类型之一（只返回单词）：
- polish: 润色、优化、改进文字
- rewrite: 重写、改写、扩写、缩写
- translate: 翻译
- format: 格式调整、排版
- chat: 普通对话、问答"""
                },
                {"role": "user", "content": message}
            ],
            max_tokens=20  # 只需要返回一个单词
        )
        
        task_type = intent_response.choices[0].message.content.strip().lower()
        
        # 验证任务类型，无效则用关键词后备
        valid_types = ["polish", "rewrite", "translate", "format", "chat"]
        if task_type not in valid_types:
            user_message_lower = message.lower()
            if any(kw in user_message_lower for kw in ["润色", "优化", "改进"]):
                task_type = "polish"
            elif any(kw in user_message_lower for kw in ["重写", "改写", "扩写", "缩写"]):
                task_type = "rewrite"
            elif any(kw in user_message_lower for kw in ["翻译", "translate"]):
                task_type = "translate"
            elif any(kw in user_message_lower for kw in ["格式", "排版"]):
                task_type = "format"
            else:
                task_type = "chat"
        
        print(f"[Stream] 任务类型: {task_type}")
        
        # 根据任务类型选择 system prompt
        # format 任务需要看到完整 JSON 结构
        system_prompts = {
            "polish": """你是专业的文字润色专家。
用户会提供文档的 JSON 结构，包含段落(paragraphs)和格式信息(runs)。
你的任务是润色文字内容，让文字更流畅优美，同时保持原有格式结构。

请返回修改后的完整 JSON，保持原有的格式属性（fontName, fontSize, bold, italic 等）不变，只修改 text 内容。
如果只需要简单润色，也可以直接返回润色后的纯文本。""",
            
            "rewrite": """你是专业的内容重写专家。
用户会提供文档的 JSON 结构，包含段落(paragraphs)和格式信息(runs)。
你的任务是根据用户要求重写内容。

如果需要保持格式，请返回修改后的完整 JSON 结构。
如果是简单重写，可以直接返回重写后的纯文本。""",
            
            "translate": """你是专业的翻译专家，精通中英文互译。
用户会提供文档的 JSON 结构。
你的任务是翻译文字内容，保持原有格式结构。

请返回翻译后的内容。如果用户需要保持格式，返回完整 JSON；否则返回纯文本翻译结果。""",
            
            "format": """你是文档格式专家。
用户会提供文档的 JSON 结构，包含：
- paragraphs: 段落数组
  - text: 段落文本
  - alignment: 对齐方式 (left/center/right/justify)
  - lineSpacing: 行间距
  - indentFirstLine: 首行缩进
  - runs: 格式块数组（包含 fontName, fontSize, bold, italic, color 等）
- tables: 表格数组
- images: 图片数组

请分析用户的格式调整需求，返回修改后的 JSON 结构。
只修改需要调整的格式属性，保持其他内容不变。""",
            
            "chat": "你是AI写作助手，帮助用户解答写作相关问题。"
        }
        
        system_prompt = system_prompts.get(task_type, system_prompts["chat"])
        
        # 构建消息
        messages = [{"role": "system", "content": system_prompt}]
        
        # 添加历史
        for msg in (history or [])[-10:]:
            if isinstance(msg, dict) and "role" in msg and "content" in msg:
                messages.append({"role": msg["role"], "content": msg["content"]})
        
        # 添加用户消息
        user_content = message
        if document_json:
            doc_text = document_json.get("text", "")
            paragraphs_count = len(document_json.get("paragraphs", []))
            tables_count = len(document_json.get("tables", []))
            images_count = len(document_json.get("images", []))
            
            print(f"[Stream] 文档结构: {paragraphs_count} 段落, {tables_count} 表格, {images_count} 图片")
            print(f"[Stream] 文档文本预览: {doc_text[:200]}..." if len(doc_text) > 200 else f"[Stream] 文档文本: {doc_text}")
            
            # 根据任务类型决定传递什么内容给 LLM
            if task_type in ["format"]:
                # 格式调整需要完整 JSON
                user_content = f"文档 JSON 结构：\n```json\n{json.dumps(document_json, ensure_ascii=False, indent=2)}\n```\n\n用户要求：{message}"
            elif task_type in ["polish", "rewrite", "translate"]:
                # 内容处理：传递简化的结构（段落 + runs），避免 JSON 太大
                simplified_json = {
                    "text": doc_text,
                    "paragraphs": []
                }
                for para in document_json.get("paragraphs", []):
                    simplified_para = {
                        "text": para.get("text", ""),
                        "alignment": para.get("alignment", "left"),
                        "styleName": para.get("styleName", ""),
                        "runs": para.get("runs", [])
                    }
                    simplified_json["paragraphs"].append(simplified_para)
                
                # 如果有表格也包含
                if document_json.get("tables"):
                    simplified_json["tables"] = document_json["tables"]
                
                user_content = f"文档结构：\n```json\n{json.dumps(simplified_json, ensure_ascii=False, indent=2)}\n```\n\n用户要求：{message}"
            else:
                # chat 模式只传纯文本
                if doc_text:
                    user_content = f"文档内容：\n{doc_text}\n\n用户问题：{message}"
        
        messages.append({"role": "user", "content": user_content})
        
        # 使用流式调用（复用之前创建的 client）
        stream = await client.chat.completions.create(
            model=settings.DEFAULT_MODEL,
            messages=messages,
            stream=True
        )
        
        # 收集完整响应用于日志
        full_response = ""
        
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                full_response += content
                yield f"data: {json.dumps({'content': content}, ensure_ascii=False)}\n\n"
        
        # 打印完整的 LLM 输出
        print("=" * 50)
        print(f"[Stream] LLM 完整输出:")
        print(full_response)
        print("=" * 50)
        
        # 如果输出中包含 JSON，尝试解析并打印
        if "{" in full_response and "}" in full_response:
            try:
                # 尝试提取 JSON 块
                import re
                json_pattern = r'```json\s*([\s\S]*?)\s*```'
                json_matches = re.findall(json_pattern, full_response)
                
                if json_matches:
                    for i, json_str in enumerate(json_matches):
                        parsed_json = json.loads(json_str)
                        print(f"[Stream] 提取的 JSON #{i+1}:")
                        print(json.dumps(parsed_json, ensure_ascii=False, indent=2))
                else:
                    # 尝试直接解析整个响应
                    # 查找第一个 { 和最后一个 }
                    start = full_response.find('{')
                    end = full_response.rfind('}') + 1
                    if start != -1 and end > start:
                        json_str = full_response[start:end]
                        parsed_json = json.loads(json_str)
                        print(f"[Stream] 提取的 JSON:")
                        print(json.dumps(parsed_json, ensure_ascii=False, indent=2))
            except json.JSONDecodeError:
                pass  # 不是有效的 JSON，忽略
            except Exception as e:
                print(f"[Stream] JSON 解析失败: {e}")
        
        # 如果有输入的文档 JSON，也打印出来供参考
        if document_json:
            print(f"[Stream] 输入的文档 JSON 结构:")
            # 只打印结构摘要，避免太长
            summary = {
                "text_length": len(document_json.get("text", "")),
                "paragraphs_count": len(document_json.get("paragraphs", [])),
                "tables_count": len(document_json.get("tables", [])),
                "images_count": len(document_json.get("images", [])),
                "has_fields": len(document_json.get("fields", [])) > 0,
                "has_TOC": document_json.get("hasTOC", False)
            }
            print(json.dumps(summary, ensure_ascii=False, indent=2))
        
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        print(f"[Stream Error] {e}")
        import traceback
        traceback.print_exc()
        yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
