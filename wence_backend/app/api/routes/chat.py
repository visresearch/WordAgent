"""
聊天处理路由
"""

import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.models.chat import ChatRequest, ChatResponse, ModelsResponse, ModelInfo
from app.core.config import settings
from app.core.agent import process_writing_request_stream

router = APIRouter()

# 可用模型列表（可以从配置文件或数据库加载）
AVAILABLE_MODELS = [
    ModelInfo(id="gpt-4", name="GPT-4", provider="OpenAI", description="强大的GPT模型"),
    ModelInfo(id="auto", name="Auto", provider="WenceAI", description="自动选择最佳模型"),
]


@router.get("/models", response_model=ModelsResponse)
async def get_models():
    """
    获取可用模型列表
    """
    return ModelsResponse(
        success=True,
        models=AVAILABLE_MODELS
    )


async def generate_stream(request: ChatRequest):
    """生成流式响应 - 使用多 Agent 系统"""
    async for chunk in process_writing_request_stream(
        message=request.message,
        document_json=request.documentJson,
        history=request.history
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
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
