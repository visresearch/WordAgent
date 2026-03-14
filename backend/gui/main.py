"""
WenCe AI GUI - 纯 PySide6 主入口
"""

import sys
import os
import subprocess
import socket
import platform

# QtWebEngine (Chromium) 不兼容 QT_OPENGL=software
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu")

# QtWebEngineWidgets 必须在 QApplication 创建之前 import
import PySide6.QtWebEngineWidgets  # noqa: F401

from PySide6.QtWidgets import QApplication
from qfluentwidgets import setTheme, Theme

IS_WINDOWS = platform.system() == "Windows"


def _find_wpscloudsvr():
    """查找 wpscloudsvr 可执行文件路径"""
    if IS_WINDOWS:
        candidates = []
        for env_var in ["LOCALAPPDATA", "PROGRAMFILES", "PROGRAMFILES(X86)"]:
            base = os.environ.get(env_var, "")
            if base:
                candidates.append(os.path.join(base, "Kingsoft", "WPS Office", "wpscloudsvr.exe"))
                candidates.append(os.path.join(base, "kingsoft", "WPS Office", "wpscloudsvr.exe"))
                candidates.append(os.path.join(base, "Kingsoft", "WPS Office", "ksolaunch.exe"))
        import shutil

        path_found = shutil.which("wpscloudsvr.exe") or shutil.which("wpscloudsvr")
        if path_found:
            candidates.insert(0, path_found)
        for c in candidates:
            if os.path.isfile(c):
                return c
        return None
    else:
        candidates = [
            "/opt/kingsoft/wps-office/office6/wpscloudsvr",
            "/usr/lib/office6/wpscloudsvr",
            "/usr/local/lib/office6/wpscloudsvr",
            os.path.expanduser("~/.local/share/wps-office/office6/wpscloudsvr"),
        ]
        for c in candidates:
            if os.path.isfile(c):
                return c
        import shutil

        return shutil.which("wpscloudsvr")


def is_port_listening(port=58890):
    """检查端口是否已有服务在监听"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            return s.connect_ex(("127.0.0.1", port)) == 0
    except Exception:
        return False


def ensure_wps_cloud_service():
    """确保 wpscloudsvr 已启动并监听 58890 端口"""
    if is_port_listening(58890):
        print("[GUI] wpscloudsvr 已在运行 (58890 端口已监听)")
        return True

    print("[GUI] 58890 端口未监听，正在启动 wpscloudsvr...")

    svr_path = _find_wpscloudsvr()
    if svr_path:
        print(f"[GUI] 找到 wpscloudsvr: {svr_path}")
        try:
            if IS_WINDOWS:
                CREATE_NO_WINDOW = 0x08000000
                subprocess.Popen(
                    [svr_path, "/jsapihttpserver", "ksowpscloudsvr://start=RelayHttpServer"],
                    creationflags=CREATE_NO_WINDOW,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                subprocess.Popen(
                    [svr_path, "/jsapihttpserver", "ksowpscloudsvr://start=RelayHttpServer"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
        except Exception as e:
            print(f"[GUI] 启动 wpscloudsvr 异常: {e}")
    else:
        print("[GUI] 未找到 wpscloudsvr，尝试系统协议唤起...")
        try:
            if IS_WINDOWS:
                os.startfile("ksoWPSCloudSvr://start=RelayHttpServer")
            else:
                subprocess.Popen(
                    ["xdg-open", "ksoWPSCloudSvr://start=RelayHttpServer"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
        except Exception as e:
            print(f"[GUI] 系统协议唤起失败: {e}")

    import time

    for i in range(10):
        time.sleep(1)
        if is_port_listening(58890):
            print(f"[GUI] wpscloudsvr 已启动 (等待了 {i + 1} 秒)")
            return True
    print("[GUI] wpscloudsvr 启动超时")
    return False


def start_gui(base_path=None):
    """启动 GUI 窗口"""
    ensure_wps_cloud_service()

    qt_app = QApplication(sys.argv)
    setTheme(Theme.LIGHT, save=True, lazy=False)

    from gui.views import MainWindow

    window = MainWindow()
    window.show()

    qt_app.exec()


if __name__ == "__main__":
    start_gui()
