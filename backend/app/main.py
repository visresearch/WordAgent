"""
WenCe AI Writing Assistant - FastAPI 应用
"""

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.responses import Response
from fastapi.staticfiles import StaticFiles

from app.api import api_router
from app.core.config import settings
from app.core.db import close_db, init_db


def get_static_dir() -> Path:
    """获取静态文件目录"""
    # 环境变量优先
    static_dir = os.environ.get("WENCE_STATIC_DIR")
    if static_dir:
        return Path(static_dir)

    # 打包后的路径（onefile 模式解压到 _MEIPASS）
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
        return base / "frontend"
    else:
        # 开发环境
        base = Path(__file__).parent.parent
        return base / "static"


def get_frontend_dist_dir() -> Path:
    """获取前端构建产物目录（dist）"""
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
        return base / "frontend"
    else:
        # 开发环境：frontend/wps_word_plugin/dist
        base = Path(__file__).parent.parent.parent
        return base / "frontend" / "wps_word_plugin" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    try:
        # 启动时初始化数据库
        await init_db()
        print("✅ 数据库初始化完成")
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        import traceback

        traceback.print_exc()
        raise

    yield

    try:
        # 关闭时清理资源
        await close_db()
        print("✅ 数据库连接已关闭")
    except Exception as e:
        print(f"⚠️ 数据库关闭出错: {e}")


app = FastAPI(
    title=settings.APP_NAME,
    description="文策 AI 写作助手后端服务",
    version=settings.VERSION,
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

# 挂载前端 dist 到 /jsplugindir/（WPS 在线插件加载路径）
FRONTEND_DIST_DIR = get_frontend_dist_dir()
if FRONTEND_DIST_DIR.exists():
    # 为 index.html 单独添加禁缓存路由（WPS 内嵌浏览器缓存过于激进）
    @app.get("/jsplugindir/")
    @app.get("/jsplugindir/index.html")
    async def serve_plugin_index():
        index_file = FRONTEND_DIST_DIR / "index.html"
        response = FileResponse(index_file, media_type="text/html")
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    app.mount("/jsplugindir", StaticFiles(directory=str(FRONTEND_DIST_DIR), html=True), name="jsplugindir")
    print(f"📂 前端插件已挂载: /jsplugindir/ -> {FRONTEND_DIST_DIR}")
else:
    print(f"⚠️  前端 dist 目录不存在: {FRONTEND_DIST_DIR}")


@app.get("/publish")
async def publish():
    """发布页 - WPS 加载项配置页面"""
    publish_file = Path(__file__).parent / "publish.html"
    return FileResponse(publish_file, media_type="text/html")


@app.get("/")
async def root():
    """根路由 - 返回前端页面或 API 信息"""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {
        "message": f"{settings.APP_NAME} is running",
        "docs": f"{settings.API_PREFIX}/docs",
        "plugin": "/plugin/manifest.xml",
    }
