"""
聊天处理路由
"""

import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Any

from app.services.agent import process_writing_request_stream
from app.models.chat import ChatRequest

router = APIRouter()


class DocumentRequest(BaseModel):
    """文档请求模型"""

    documentJson: Any  # 文档 JSON 数据
    documentName: str = ""  # 文档名称
    timestamp: int | None = None


async def generate_stream(request: ChatRequest):
    """生成流式响应 - 使用 Agent + Tool Calling"""
    async for chunk in process_writing_request_stream(
        message=request.message,
        document_json=request.documentJson,
        history=request.history,
        model=request.model,
        mode=request.mode,
    ):
        yield chunk


@router.post("/doc")
async def receive_document(request: DocumentRequest):
    """
    接收文档 JSON 接口
    用于接收前端解析的全文文档
    """
    doc_json = request.documentJson
    doc_name = request.documentName

    # 统计文档信息
    para_count = len(doc_json.get("paragraphs", [])) if doc_json else 0
    table_count = len(doc_json.get("tables", [])) if doc_json else 0
    meta = doc_json.get("_meta", {}) if doc_json else {}

    print("=" * 50)
    print("收到文档:")
    print(f"文档名: {doc_name or meta.get('documentName', '未知')}")
    print(f"段落数: {para_count}")
    print(f"表格数: {table_count}")
    print("=" * 50)

    return {
        "success": True,
        "message": "文档接收成功",
        "stats": {
            "paragraphCount": para_count,
            "tableCount": table_count,
            "documentName": doc_name or meta.get("documentName", ""),
            "isFullDocument": meta.get("isFullDocument", False),
        },
    }


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """
    流式聊天接口
    使用 SSE 返回流式响应
    """
    print("=" * 50)
    print("收到流式聊天请求:")
    print(f"用户消息: {request.message}")
    print(f"模式: {request.mode}")
    print(f"模型: {request.model}")
    if request.documentJson:
        para_count = len(request.documentJson.get("paragraphs", []))
        print(f"文档段落数: {para_count}")
    print("=" * 50)

    return StreamingResponse(
        generate_stream(request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )
