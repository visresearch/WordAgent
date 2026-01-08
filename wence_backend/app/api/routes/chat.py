"""
聊天处理路由
"""

import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI
from app.models.chat import ChatRequest, ChatResponse, ModelsResponse, ModelInfo
from app.core.config import settings

router = APIRouter()

# OpenAI 客户端
client = AsyncOpenAI(
    api_key=settings.OPENAI_API_KEY,
    base_url=settings.OPENAI_BASE_URL if settings.OPENAI_BASE_URL else None
)

# 可用模型列表（可以从配置文件或数据库加载）
AVAILABLE_MODELS = [
    ModelInfo(id="gpt-5", name="GPT-5", provider="OpenAI", description="最强大的GPT模型"),
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
    """生成流式响应"""
    try:
        # 构建消息列表
        messages = [
            {"role": "system", "content": "你是一个专业的AI写作助手，帮助用户修改和优化文档内容。"}
        ]
        
        # 添加历史消息
        for msg in request.history[-10:]:  # 最多取最近10条
            if isinstance(msg, dict) and "role" in msg and "content" in msg:
                messages.append({"role": msg["role"], "content": msg["content"]})
        
        # 如果有文档内容，添加到用户消息中
        user_content = request.message
        if request.documentJson:
            user_content = f"以下是用户选中的文档内容：\n```json\n{json.dumps(request.documentJson, ensure_ascii=False, indent=2)}\n```\n\n用户请求：{request.message}"
        
        messages.append({"role": "user", "content": user_content})
        
        # 调用 OpenAI 流式 API
        stream = await client.chat.completions.create(
            model=request.model if request.model != "auto" else settings.DEFAULT_MODEL,
            messages=messages,
            stream=True
        )
        
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                # SSE 格式
                yield f"data: {json.dumps({'content': content}, ensure_ascii=False)}\n\n"
        
        # 发送结束标记
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        print(f"流式生成错误: {e}")
        yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"


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


@router.post("/request", response_model=ChatResponse)
async def chat_request(request: ChatRequest):
    """
    聊天接口（非流式）
    接收用户消息，返回 AI 回复
    """
    # 打印收到的请求
    print("=" * 50)
    print("收到聊天请求:")
    print(f"用户消息: {request.message}")
    print(f"模式: {request.mode}")
    print(f"模型: {request.model}")
    print(f"历史消息数: {len(request.history)}")
    print(f"时间戳: {request.timestamp}")
    if request.documentJson:
        print(f"文档 JSON: {request.documentJson}")
    print("=" * 50)
    
    try:
        # 构建消息列表
        messages = [
            {"role": "system", "content": "你是一个专业的AI写作助手，帮助用户修改和优化文档内容。"}
        ]
        
        for msg in request.history[-10:]:
            if isinstance(msg, dict) and "role" in msg and "content" in msg:
                messages.append({"role": msg["role"], "content": msg["content"]})
        
        user_content = request.message
        if request.documentJson:
            user_content = f"以下是用户选中的文档内容：\n```json\n{json.dumps(request.documentJson, ensure_ascii=False, indent=2)}\n```\n\n用户请求：{request.message}"
        
        messages.append({"role": "user", "content": user_content})
        
        # 调用 OpenAI API
        response = await client.chat.completions.create(
            model=request.model if request.model != "auto" else settings.DEFAULT_MODEL,
            messages=messages
        )
        
        reply = response.choices[0].message.content
        
        return ChatResponse(
            success=True,
            message=reply,
            data={"reply": reply}
        )
        
    except Exception as e:
        print(f"API 调用错误: {e}")
        return ChatResponse(
            success=False,
            message=f"AI 服务错误: {str(e)}",
            data=None
        )
