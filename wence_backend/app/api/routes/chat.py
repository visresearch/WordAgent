"""
聊天处理路由
"""

from fastapi import APIRouter
from app.models.chat import ChatRequest, ChatResponse

router = APIRouter()


@router.post("/request", response_model=ChatResponse)
async def chat_request(request: ChatRequest):
    """
    聊天接口
    接收用户消息，返回 AI 回复
    """
    # 打印收到的请求
    print("=" * 50)
    print("收到聊天请求:")
    print(f"用户消息: {request.message}")
    print(f"模型: {request.model}")
    print(f"历史消息数: {len(request.history)}")
    print(f"时间戳: {request.timestamp}")
    print("=" * 50)
    
    # TODO: 调用 AI 服务处理
    
    return ChatResponse(
        success=True,
        message="请求已收到",
        data={"reply": f"收到消息: {request.message}"}
    )
