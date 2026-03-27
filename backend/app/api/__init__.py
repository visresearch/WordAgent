"""
WenCe AI Writing Assistant - API 模块
"""

from fastapi import APIRouter

from app.api.routes import chat, files, models, sessions, settings

api_router = APIRouter()

# 注册路由
api_router.include_router(chat.router, prefix="/chat", tags=["聊天处理"])
api_router.include_router(models.router, prefix="/chat", tags=["模型列表"])
api_router.include_router(files.router, prefix="/chat", tags=["文件上传"])
api_router.include_router(sessions.router, tags=["会话管理"])
api_router.include_router(settings.router, tags=["设置管理"])
