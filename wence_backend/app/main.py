"""
WenCe AI Writing Assistant - FastAPI 应用
"""

import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.db import init_db, close_db
from app.api import api_router


def get_static_dir() -> Path:
    """获取静态文件目录"""
    # 打包后的路径
    if getattr(sys, 'frozen', False):
        base = Path(sys.executable).parent
    else:
        # 开发环境
        base = Path(__file__).parent.parent
    
    static_dir = os.environ.get("WENCE_STATIC_DIR")
    if static_dir:
        return Path(static_dir)
    
    return base / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化数据库
    await init_db()
    print("✅ 数据库初始化完成")
    yield
    # 关闭时清理资源
    await close_db()
    print("✅ 数据库连接已关闭")


app = FastAPI(
    title=settings.APP_NAME,
    description="文策 AI 写作助手后端服务",
    version=settings.VERSION,
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc",
    lifespan=lifespan,
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

# 挂载静态文件（打包后使用）
STATIC_DIR = get_static_dir()
if STATIC_DIR.exists():
    # 挂载插件目录 - 用于 WPS 加载在线插件
    plugin_dir = STATIC_DIR / "plugin"
    if plugin_dir.exists():
        app.mount("/plugin", StaticFiles(directory=str(plugin_dir)), name="plugin")
    
    # 挂载前端静态资源
    assets_dir = STATIC_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")


@app.get("/")
async def root():
    """根路由 - 返回前端页面或 API 信息"""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {
        "message": f"{settings.APP_NAME} is running",
        "docs": f"{settings.API_PREFIX}/docs",
        "plugin": "/plugin/manifest.xml"
    }
