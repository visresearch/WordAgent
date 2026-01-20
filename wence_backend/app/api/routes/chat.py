"""
聊天处理路由
"""

import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

# 使用纯 LangChain 版本（完美流式输出）
from app.services.agent import process_writing_request_stream
from app.models.chat import ChatRequest

router = APIRouter()


async def generate_stream(request: ChatRequest):
    """生成流式响应 - 使用 Agent + Tool Calling"""
    async for chunk in process_writing_request_stream(
        message=request.message,
        document_json=request.documentJson,
        history=request.history,
        model=request.model,  # 传递用户选择的模型
        mode=request.mode,  # 传递对话模式
    ):
        yield chunk


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
    print(f"文档 JSON: {json.dumps(request.documentJson, ensure_ascii=False, indent=2)}")
    print("=" * 50)

    return StreamingResponse(
        generate_stream(request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )
