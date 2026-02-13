"""
WenCe AI GUI - publish.html 窗口
"""

import sys
import os
import subprocess
import socket
import platform

os.environ["QT_OPENGL"] = "software"

from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineScript, QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView

IS_WINDOWS = platform.system() == "Windows"


def _find_wpscloudsvr():
    """查找 wpscloudsvr 可执行文件路径"""
    if IS_WINDOWS:
        # Windows 常见安装路径
        candidates = []
        for env_var in ["LOCALAPPDATA", "PROGRAMFILES", "PROGRAMFILES(X86)"]:
            base = os.environ.get(env_var, "")
            if base:
                candidates.append(os.path.join(base, "Kingsoft", "WPS Office", "wpscloudsvr.exe"))
                candidates.append(os.path.join(base, "kingsoft", "WPS Office", "wpscloudsvr.exe"))
                # 新版 WPS 路径
                candidates.append(os.path.join(base, "Kingsoft", "WPS Office", "ksolaunch.exe"))
        # 也在 PATH 中搜索
        import shutil
        path_found = shutil.which("wpscloudsvr.exe") or shutil.which("wpscloudsvr")
        if path_found:
            candidates.insert(0, path_found)
        for c in candidates:
            if os.path.isfile(c):
                return c
        return None
    else:
        # Linux: 多个可能的安装路径
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
    """检查 58890 端口是否已有服务在监听"""
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

    # 优先直接启动 wpscloudsvr 进程
    svr_path = _find_wpscloudsvr()
    if svr_path:
        print(f"[GUI] 找到 wpscloudsvr: {svr_path}")
        try:
            if IS_WINDOWS:
                # Windows: 使用 CREATE_NO_WINDOW 避免弹出命令行窗口
                CREATE_NO_WINDOW = 0x08000000
                subprocess.Popen(
                    [svr_path, "/jsapihttpserver",
                     "ksowpscloudsvr://start=RelayHttpServer"],
                    creationflags=CREATE_NO_WINDOW,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                # Linux
                subprocess.Popen(
                    [svr_path, "/jsapihttpserver",
                     "ksowpscloudsvr://start=RelayHttpServer"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
        except Exception as e:
            print(f"[GUI] 启动 wpscloudsvr 异常: {e}")
    else:
        # 找不到 wpscloudsvr，尝试用系统协议唤起
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

    # 等待服务启动
    import time
    for i in range(10):
        time.sleep(1)
        if is_port_listening(58890):
            print(f"[GUI] wpscloudsvr 已启动 (等待了 {i+1} 秒)")
            return True
    print("[GUI] wpscloudsvr 启动超时")
    return False


class SafeWebPage(QWebEnginePage):
    def acceptNavigationRequest(self, url, nav_type, is_main_frame):
        """拦截自定义协议导航，防止页面跳走"""
        scheme = url.scheme().lower()
        if scheme == "ksowpscloudsvr":
            print("[GUI] 拦截到自定义协议导航，直接启动 wpscloudsvr")
            ensure_wps_cloud_service()
            return False
        return True

    def javaScriptConsoleMessage(self, level, message, line, source):
        """拦截 JS console 消息，处理自定义协议启动"""
        if message.startswith("[WPSLAUNCH]"):
            print(f"[GUI] JS 请求启动 WPS 服务")
            ensure_wps_cloud_service()
        else:
            super().javaScriptConsoleMessage(level, message, line, source)


def start_gui(base_path=None):
    """启动 GUI 窗口，base_path 用于兼容 PyInstaller 打包路径"""
    # 在打开界面前先确保 wpscloudsvr 已启动
    ensure_wps_cloud_service()

    qt_app = QApplication(sys.argv)

    view = QWebEngineView()
    page = SafeWebPage(view)
    view.setPage(page)

    settings = page.settings()
    settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
    settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)

    # 直接加载后端 /publish 页面
    view.setUrl(QUrl("http://127.0.0.1:3880/publish"))

    view.resize(900, 600)
    view.setWindowTitle("WPS 加载项配置")
    view.show()

    qt_app.exec()


if __name__ == "__main__":
    start_gui()
