"""
多 Agent 协作系统 - 使用 Tool Calling
简化为 3 个 Agent：Router、Content、Format
"""

from typing import AsyncGenerator
import json
from openai import AsyncOpenAI
from app.core.config import settings


# ============== Tool 定义 ==============

# 定义 tools schema（与 docxJsonConverter.js 保持一致）
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "generate_document",
            "description": "生成带格式的文档 JSON，用于输出到 Word 文档。",
            "parameters": {
                "type": "object",
                "properties": {
                    "paragraphs": {
                        "type": "array",
                        "description": "段落数组",
                        "items": {
                            "type": "object",
                            "properties": {
                                "text": {"type": "string", "description": "段落完整文本"},
                                "alignment": {"type": "string", "enum": ["left", "center", "right", "justify"], "description": "对齐方式"},
                                "lineSpacing": {"type": "number", "description": "行间距"},
                                "indentLeft": {"type": "number", "description": "左缩进"},
                                "indentRight": {"type": "number", "description": "右缩进"},
                                "indentFirstLine": {"type": "number", "description": "首行缩进"},
                                "spaceBefore": {"type": "number", "description": "段前间距"},
                                "spaceAfter": {"type": "number", "description": "段后间距"},
                                "styleName": {"type": "string", "description": "样式名称，如 '标题 1', '标题 2', '正文'"},
                                "runs": {
                                    "type": "array",
                                    "description": "格式块数组，每个 run 是一段具有相同格式的文字",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "text": {"type": "string", "description": "文字内容"},
                                            "fontName": {"type": "string", "description": "字体名称，如 '宋体', 'Times New Roman'"},
                                            "fontSize": {"type": "number", "description": "字号"},
                                            "bold": {"type": "boolean", "description": "是否加粗"},
                                            "italic": {"type": "boolean", "description": "是否斜体"},
                                            "underline": {"type": "string", "enum": ["none", "single", "double", "thick"], "description": "下划线"},
                                            "color": {"type": "string", "description": "颜色，如 '#000000'"},
                                            "highlight": {"type": "string", "description": "高亮色"},
                                            "strikethrough": {"type": "boolean", "description": "是否删除线"},
                                            "superscript": {"type": "boolean", "description": "是否上标"},
                                            "subscript": {"type": "boolean", "description": "是否下标"}
                                        },
                                        "required": ["text"]
                                    }
                                }
                            },
                            "required": ["text", "runs"]
                        }
                    },
                    "tables": {
                        "type": "array",
                        "description": "表格数组",
                        "items": {
                            "type": "object",
                            "properties": {
                                "rows": {"type": "number", "description": "行数"},
                                "columns": {"type": "number", "description": "列数"},
                                "tableAlignment": {"type": "string", "enum": ["left", "center", "right"], "description": "表格对齐"},
                                "cells": {
                                    "type": "array",
                                    "description": "单元格二维数组",
                                    "items": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "text": {"type": "string"},
                                                "rowSpan": {"type": "number"},
                                                "colSpan": {"type": "number"},
                                                "alignment": {"type": "string"},
                                                "verticalAlignment": {"type": "string"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                "required": ["paragraphs"]
            }
        }
    }
]


# ============== System Prompts ==============

ROUTER_PROMPT = """分析用户请求，返回以下任务类型之一（只返回单词）：
- content: 润色、优化、改进、重写、改写、扩写、缩写、翻译
- format: 格式调整、排版、字体、字号、对齐、缩进
- chat: 普通对话、问答、解释说明"""

CONTENT_PROMPT = """你是专业的文档内容处理专家，负责润色、重写、翻译等任务。

【核心原则】格式属性必须100%复制原值！
除非用户明确说"改格式"、"调整格式"等，否则所有格式属性必须与原文档完全一致。

【必须原样复制的格式属性】
段落级别：
- alignment: 原值是什么就写什么
- lineSpacing: 原值是什么就写什么（如18就是18，不要改成12）
- indentFirstLine: 原值是什么就写什么（如24就是24，不要改成0）
- indentLeft, indentRight: 原值是什么就写什么
- spaceBefore, spaceAfter: 原值是什么就写什么（如0就是0，不要改成8.3）
- styleName: 原值是什么就写什么

Run级别（每个格式块）：
- fontName, fontSize, bold, italic, underline, color 等: 全部原样复制

【你只能修改的内容】
- runs 里的 text 字段（文字内容）
- paragraphs 里的 text 字段（段落完整文本）

【工作流程】
1. 先简要说明你的修改（1-2句话）
2. 调用 generate_document，格式属性直接从原文档复制粘贴

【扩写新增段落时】
新段落要沿用相邻段落的完整格式（包括 lineSpacing=18, indentFirstLine=24 等）

示例：如果原文档段落格式是 lineSpacing:18, indentFirstLine:24, spaceBefore:0, spaceAfter:0
你生成的段落也必须是 lineSpacing:18, indentFirstLine:24, spaceBefore:0, spaceAfter:0"""

FORMAT_PROMPT = """你是文档格式专家，负责调整文档的排版格式。

工作流程：
1. 先用简短的文字说明你要做什么格式调整（1-2句话）
2. 然后调用 generate_document 工具输出调整后的文档

可调整的格式属性：
- alignment: 对齐方式 (left/center/right/justify)
- runs 中的格式：fontName(字体), fontSize(字号), bold(加粗), italic(斜体), color(颜色)
- styleName: 段落样式

注意：保持文本内容不变，只修改格式属性。"""

CHAT_PROMPT = """你是 AI 写作助手，帮助用户解答问题。
如果用户想修改文档，引导他们使用具体的功能（润色、重写、翻译、格式调整等）。
直接用文字回答，不需要调用工具。"""


# ============== 核心处理函数 ==============

async def process_writing_request_stream(
    message: str,
    document_json: dict | None = None,
    history: list | None = None
) -> AsyncGenerator[str, None]:
    """
    处理写作请求（流式版本 + Tool Calling）
    
    输出两种类型的 SSE 消息：
    - type: text - 显示给用户的文字说明
    - type: json - 生成的文档 JSON（用于输出到 Word）
    """
    try:
        client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL if settings.OPENAI_BASE_URL else None
        )
        
        # ===== Step 1: 意图识别 =====
        intent_response = await client.chat.completions.create(
            model=settings.DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": ROUTER_PROMPT},
                {"role": "user", "content": message}
            ],
            max_tokens=20
        )
        
        task_type = intent_response.choices[0].message.content.strip().lower()
        
        # 验证并修正任务类型
        if task_type not in ["content", "format", "chat"]:
            msg_lower = message.lower()
            if any(kw in msg_lower for kw in ["润色", "优化", "改进", "重写", "改写", "扩写", "缩写", "翻译"]):
                task_type = "content"
            elif any(kw in msg_lower for kw in ["格式", "排版", "字体", "字号", "对齐"]):
                task_type = "format"
            else:
                task_type = "chat"
        
        print(f"[Agent] 任务类型: {task_type}")
        
        # ===== Step 2: 选择 prompt 和是否使用 tools =====
        if task_type == "content":
            system_prompt = CONTENT_PROMPT
            use_tools = True
        elif task_type == "format":
            system_prompt = FORMAT_PROMPT
            use_tools = True
        else:
            system_prompt = CHAT_PROMPT
            use_tools = False
        
        # ===== Step 3: 构建消息 =====
        messages = [{"role": "system", "content": system_prompt}]
        
        # 添加历史
        for msg in (history or [])[-6:]:
            if isinstance(msg, dict) and "role" in msg and "content" in msg:
                messages.append({"role": msg["role"], "content": msg["content"]})
        
        # 构建用户消息
        user_content = message
        if document_json and task_type in ["content", "format"]:
            # 保留完整的格式属性，不要简化！
            simplified = {
                "text": document_json.get("text", ""),
                "paragraphs": []
            }
            for para in document_json.get("paragraphs", []):
                # 保留所有格式属性
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
            if document_json.get("tables"):
                simplified["tables"] = document_json["tables"]

            user_content = f"文档结构（格式属性必须原样复制）：\n```json\n{json.dumps(simplified, ensure_ascii=False, indent=2)}\n```\n\n用户要求：{message}"
            print(f"[Agent] 文档: {len(simplified['paragraphs'])} 段落")
        elif document_json and task_type == "chat":
            doc_text = document_json.get("text", "")
            if doc_text:
                user_content = f"文档内容：\n{doc_text[:1000]}\n\n用户问题：{message}"
        
        messages.append({"role": "user", "content": user_content})
        
        # ===== Step 4: 调用 LLM =====
        if use_tools:
            # ===== 第一次调用：流式输出文字说明 =====
            explain_prompt = system_prompt + "\n\n请先简要说明你将如何处理这个请求（1-2句话），不要输出JSON或调用工具。"
            explain_messages = [{"role": "system", "content": explain_prompt}]
            explain_messages.append({"role": "user", "content": user_content})
            
            response1 = await client.chat.completions.create(
                model=settings.DEFAULT_MODEL,
                messages=explain_messages,
                stream=True,
                max_tokens=200  # 限制说明文字长度
            )
            
            text_content = ""
            async for chunk in response1:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    text_content += content
                    yield f"data: {json.dumps({'type': 'text', 'content': content}, ensure_ascii=False)}\n\n"
            
            print(f"[Agent] 说明文字: {text_content[:100]}...")
            
            # ===== 第二次调用：强制调用 tool 生成文档 =====
            response2 = await client.chat.completions.create(
                model=settings.DEFAULT_MODEL,
                messages=messages,
                tools=TOOLS,
                tool_choice={"type": "function", "function": {"name": "generate_document"}},
                stream=True
            )
            
            # 收集 tool call 数据
            tool_calls_data = {}
            
            async for chunk in response2:
                delta = chunk.choices[0].delta if chunk.choices else None
                if not delta:
                    continue
                
                # 处理 tool calls
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in tool_calls_data:
                            tool_calls_data[idx] = {"id": "", "name": "", "arguments": ""}
                        if tc.id:
                            tool_calls_data[idx]["id"] = tc.id
                        if tc.function:
                            if tc.function.name:
                                tool_calls_data[idx]["name"] = tc.function.name
                            if tc.function.arguments:
                                tool_calls_data[idx]["arguments"] += tc.function.arguments
            
            # 处理收集到的 tool calls
            for idx, tc_data in tool_calls_data.items():
                if tc_data["name"] == "generate_document":
                    try:
                        doc_json = json.loads(tc_data["arguments"])
                        print(f"[Agent] Tool 调用成功，生成 {len(doc_json.get('paragraphs', []))} 段落")
                        
                        # 发送 JSON 数据
                        yield f"data: {json.dumps({'type': 'json', 'content': doc_json}, ensure_ascii=False)}\n\n"
                    except json.JSONDecodeError as e:
                        print(f"[Agent] Tool 参数解析失败: {e}")
                        error_msg = f"\n\n⚠️ 生成文档失败: {e}"
                        yield f"data: {json.dumps({'type': 'text', 'content': error_msg}, ensure_ascii=False)}\n\n"
            
        else:
            # 普通聊天模式，不使用 tools
            response = await client.chat.completions.create(
                model=settings.DEFAULT_MODEL,
                messages=messages,
                stream=True
            )
            
            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    yield f"data: {json.dumps({'type': 'text', 'content': content}, ensure_ascii=False)}\n\n"
        
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        print(f"[Agent Error] {e}")
        import traceback
        traceback.print_exc()
        yield f"data: {json.dumps({'type': 'text', 'content': f'错误: {str(e)}'}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
