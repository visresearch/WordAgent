"""
WenCe AI Writing Assistant - FastAPI 应用
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api import api_router


app = FastAPI(
    title=settings.APP_NAME,
    description="文策 AI 写作助手后端服务",
    version=settings.VERSION,
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc",
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册 API 路由
app.include_router(api_router, prefix=settings.API_PREFIX)


@app.get("/")
async def root():
    """根路由"""
    return {
        "message": f"{settings.APP_NAME} is running",
        "docs": f"{settings.API_PREFIX}/docs"
    }
