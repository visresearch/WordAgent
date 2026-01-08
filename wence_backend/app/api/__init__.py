"""
WenCe AI Writing Assistant - API 模块
"""

from fastapi import APIRouter
from app.api.routes import chat, health

api_router = APIRouter()

# 注册路由
api_router.include_router(health.router, tags=["健康检查"])
api_router.include_router(chat.router, prefix="/chat", tags=["聊天处理"])
