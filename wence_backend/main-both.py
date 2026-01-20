"""
WenCe AI Writing Assistant - 入口文件
支持启动 GUI 界面和 FastAPI 服务
"""

import sys
import argparse
import threading
import uvicorn


def start_api_server():
    """启动 FastAPI 服务"""
    try:
        from app.core.config import settings

        print("🚀 启动 WenCe AI Writing Assistant API 服务...")
        print(f"📍 访问地址: http://{settings.HOST}:{settings.PORT}")
        print(f"📚 API 文档: http://{settings.HOST}:{settings.PORT}{settings.API_PREFIX}/docs")

        uvicorn.run(
            "app.main:app",
            host=settings.HOST,
            port=settings.PORT,
            reload=False,  # GUI 模式下禁用热重载
            log_level="info",
            access_log=True,
        )
    except Exception as e:
        print(f"❌ API 服务启动失败: {e}")
        import traceback

        traceback.print_exc()


def start_gui():
    """启动 GUI 界面"""
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QApplication
        from qfluentwidgets import setTheme, Theme, setThemeColor

        from gui.views.main_window import MainWindow

        print("🎨 启动 GUI 界面...")

        # 启用高DPI缩放
        QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

        app = QApplication(sys.argv)

        # 设置主题
        setTheme(Theme.AUTO)
        setThemeColor("#0078D4")  # 微软蓝色

        # 创建主窗口
        window = MainWindow()
        window.show()

        print("✅ GUI 界面启动成功")

        sys.exit(app.exec())

    except Exception as e:
        print(f"❌ GUI 启动失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


def start_gui_with_api():
    """同时启动 GUI 和 API 服务"""
    # 在后台线程启动 API 服务
    api_thread = threading.Thread(target=start_api_server, daemon=True)
    api_thread.start()

    # 在主线程启动 GUI
    start_gui()


def start_api_only():
    """仅启动 API 服务"""
    import signal

    def signal_handler(sig, frame):
        print("\n正在安全关闭服务...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    start_api_server()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WenCe AI Writing Assistant")
    parser.add_argument(
        "--mode",
        choices=["gui", "api", "both"],
        default="both",
        help="启动模式: gui(仅GUI), api(仅API), both(GUI+API, 默认)",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("🤖 WenCe AI Writing Assistant")
    print("=" * 60)

    try:
        if args.mode == "gui":
            print("📋 模式: 仅 GUI 界面")
            start_gui()
        elif args.mode == "api":
            print("📋 模式: 仅 API 服务")
            start_api_only()
        else:  # both
            print("📋 模式: GUI + API 服务")
            start_gui_with_api()

    except KeyboardInterrupt:
        print("\n👋 程序已退出")
        sys.exit(0)
    except Exception as e:
        print(f"❌ 程序异常退出: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
