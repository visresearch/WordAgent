"""
WenCe AI Writing Assistant - 入口文件
启动 FastAPI 服务和前端插件
"""

import sys
import signal
import threading
import time
import os
from pathlib import Path


def get_base_path():
    """获取基础路径，支持 PyInstaller 打包后运行"""
    if getattr(sys, "frozen", False):
        # PyInstaller 打包后运行
        return Path(sys._MEIPASS)
    else:
        # 正常 Python 运行
        return Path(__file__).parent


def start_frontend():
    """启动前端静态文件服务器"""
    try:
        base_path = get_base_path()

        # PyInstaller 打包后在 frontend 目录
        frontend_build_dir = base_path / "frontend"

        # 如果打包目录不存在，尝试开发环境路径
        if not frontend_build_dir.exists():
            frontend_build_dir = Path(__file__).parent.parent / "wence_frontend" / "wence_word_plugin" / "dist"

        if not frontend_build_dir.exists():
            print("⚠️  前端构建目录不存在，跳过启动前端服务")
            return

        print(f"🎨 启动前端插件服务器 (端口 3889)...")
        print(f"📂 静态文件目录: {frontend_build_dir}")

        # 使用 Python 内置 HTTP 服务器提供静态文件
        import http.server
        import socketserver

        # 不改变工作目录，而是使用自定义 Handler
        class CustomHandler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(frontend_build_dir), **kwargs)

        with socketserver.TCPServer(("", 3889), CustomHandler) as httpd:
            print(f"✅ 前端服务启动成功: http://localhost:3889")
            httpd.serve_forever()

    except Exception as e:
        print(f"⚠️  前端服务启动失败: {e}")


def start_api_server():
    """启动 FastAPI 服务"""
    try:
        import uvicorn
        from app.core.config import settings
        from app.main import app

        print("🚀 启动 WenCe AI Writing Assistant API 服务...")
        print(f"📍 访问地址: http://{settings.HOST}:{settings.PORT}")

        # 打包后直接使用 app 对象，而不是字符串导入
        uvicorn.run(
            app,
            host=settings.HOST,
            port=settings.PORT,
            reload=False,
            log_level="info",
            access_log=True,
        )
    except Exception as e:
        print(f"❌ API 服务启动失败: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":

    def signal_handler(sig, frame):
        print("\n正在安全关闭服务...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print(r"""
██╗    ██╗███████╗███╗   ██╗ ██████╗███████╗     █████╗ ██╗
██║    ██║██╔════╝████╗  ██║██╔════╝██╔════╝    ██╔══██╗██║
██║ █╗ ██║█████╗  ██╔██╗ ██║██║     █████╗      ███████║██║
██║███╗██║██╔══╝  ██║╚██╗██║██║     ██╔══╝      ██╔══██║██║
╚███╔███╔╝███████╗██║ ╚████║╚██████╗███████╗    ██║  ██║██║
 ╚══╝╚══╝ ╚══════╝╚═╝  ╚═══╝ ╚═════╝╚══════╝    ╚═╝  ╚═╝╚═╝
    """)

    try:
        # 在后台线程启动 API 服务
        api_thread = threading.Thread(target=start_api_server, daemon=True)
        api_thread.start()

        # 等待 API 服务启动
        time.sleep(1)

        # 在后台线程启动前端服务
        # frontend_thread = threading.Thread(target=start_frontend, daemon=True)
        # frontend_thread.start()

        # 主线程保持运行
        print("\n✅ 所有服务已启动，按 Ctrl+C 退出")
        while True:
            time.sleep(1)

        # start_frontend()
        # time.sleep(1)
        # api_thread = threading.Thread(target=start_api_server, daemon=True)
        # api_thread.start()
    except KeyboardInterrupt:
        print("\n👋 程序已退出")
        sys.exit(0)
    except Exception as e:
        print(f"❌ 程序异常退出: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
