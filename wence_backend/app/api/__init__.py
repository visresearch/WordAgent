"""
WenCe AI Writing Assistant - API 模块
"""

from fastapi import APIRouter

from app.api.routes import chat, health, history, models

api_router = APIRouter()

# 注册路由
api_router.include_router(health.router, tags=["健康检查"])
api_router.include_router(chat.router, prefix="/chat", tags=["聊天处理"])
api_router.include_router(models.router, prefix="/chat", tags=["模型列表"])
api_router.include_router(history.router, prefix="/chat", tags=["聊天历史"])
