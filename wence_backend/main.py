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


def start_gui():
    """启动 GUI 桌面程序"""
    sys.path.insert(0, str(Path(__file__).parent))
    from gui.main import start_gui as _start_gui

    _start_gui(base_path=str(get_base_path()))


if __name__ == "__main__":

    def signal_handler(sig, frame):
        print("\n正在安全关闭服务...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 尽早安装 OutputBuffer，这样 uvicorn / logging 拿到的
    # sys.stdout / sys.stderr 都是我们的 wrapper，终端界面才能显示所有输出
    from gui.views.console_interface import OutputBuffer

    OutputBuffer.install()

    print(r"""
██╗    ██╗███████╗███╗   ██╗ ██████╗███████╗     █████╗ ██╗
██║    ██║██╔════╝████╗  ██║██╔════╝██╔════╝    ██╔══██╗██║
██║ █╗ ██║█████╗  ██╔██╗ ██║██║     █████╗      ███████║██║
██║███╗██║██╔══╝  ██║╚██╗██║██║     ██╔══╝      ██╔══██║██║
╚███╔███╔╝███████╗██║ ╚████║╚██████╗███████╗    ██║  ██║██║
 ╚══╝╚══╝ ╚══════╝╚═╝  ╚═══╝ ╚═════╝╚══════╝    ╚═╝  ╚═╝╚═╝
    """)

    gui_proc = None
    try:
        # 在后台线程启动 API 服务
        api_thread = threading.Thread(target=start_api_server, daemon=True)
        api_thread.start()

        # 等待 1 秒确保 API 先就绪
        time.sleep(1)

        # 在主线程启动 GUI（Qt 必须在主线程运行）
        print("🖥️  启动 GUI 桌面程序...")
        start_gui()

        # GUI 关闭后退出
        print("🖥️  GUI 已关闭，正在退出...")
        os._exit(0)

    except KeyboardInterrupt:
        print("\n👋 程序已退出")
        sys.exit(0)
    except Exception as e:
        print(f"❌ 程序异常退出: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
