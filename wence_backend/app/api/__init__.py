"""
WenCe AI Writing Assistant - API 模块
"""

from fastapi import APIRouter

from app.api.routes import chat, history, models, settings

api_router = APIRouter()

# 注册路由
api_router.include_router(chat.router, prefix="/chat", tags=["聊天处理"])
api_router.include_router(models.router, prefix="/chat", tags=["模型列表"])
api_router.include_router(history.router, prefix="/chat", tags=["聊天历史"])
api_router.include_router(settings.router, tags=["设置管理"])
