"""
WenCe AI GUI - 纯 PySide6 主入口
"""

import sys
import os
import subprocess
import socket
import platform
from pathlib import Path

# 独立启动 GUI 时也必须在导入 Qt 前配置渲染。
os.environ.setdefault("QT_WIDGETS_RHI", "0")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu")
if sys.platform == "linux":
    os.environ.setdefault("QT_XCB_GL_INTEGRATION", "none")
    os.environ.setdefault("QT_QUICK_BACKEND", "software")
    if getattr(sys, "frozen", False):
        bundle_dir = Path(sys._MEIPASS)
        os.environ.setdefault("GIO_MODULE_DIR", str(bundle_dir / "gio" / "modules"))
        os.environ.setdefault("GIO_EXTRA_MODULES", "")

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon
from qfluentwidgets import setTheme, Theme

from app.core.logging import get_logger
from gui.i18n import get_locale, set_locale, subscribe_locale_changed, t

IS_WINDOWS = platform.system() == "Windows"
logger = get_logger(__name__)


def _icon_path(name: str) -> str:
    """获取 GUI 图标文件路径"""
    return str(Path(__file__).parent / "resources" / "icon" / name)


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
        # WPS 支持安装到自定义目录，实际安装路径以系统注册信息为准。
        import winreg

        registry_paths = [
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\wps.exe"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\wps.exe"),
            (winreg.HKEY_CLASSES_ROOT, r"ksowpscloudsvr\shell\open\command"),
        ]
        for root, key_path in registry_paths:
            try:
                with winreg.OpenKey(root, key_path) as key:
                    command = str(winreg.QueryValueEx(key, "")[0]).strip()
            except OSError:
                continue
            if command.startswith('"'):
                executable = command.split('"', 2)[1]
            else:
                end = command.lower().find(".exe")
                if end < 0:
                    continue
                executable = command[: end + 4]
            executable = os.path.expandvars(executable)
            candidates.insert(0, os.path.join(os.path.dirname(executable), "wpscloudsvr.exe"))
            if os.path.basename(executable).lower() in {"wpscloudsvr.exe", "ksolaunch.exe"}:
                candidates.append(executable)
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
    """确保 wpscloudsvr 已启动并监听 58890 端口。

    Only starts the service when WPS is actually installed. If WPS is not
    installed, skip silently (debug log only) so users without WPS don't see
    warnings or suffer a 10-second startup delay.
    """
    if is_port_listening(58890):
        logger.info("wpscloudsvr 已在运行 (58890 端口已监听)")
        return True

    svr_path = _find_wpscloudsvr()
    if not svr_path:
        # WPS not installed — skip silently, no protocol wakeup, no waiting.
        logger.debug("WPS not installed, skipping wpscloudsvr startup")
        return False

    logger.info("58890 端口未监听，正在启动 wpscloudsvr")
    logger.info("找到 wpscloudsvr: %s", svr_path)
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
        logger.warning("启动 wpscloudsvr 异常: %s", e)
        return False

    import time

    for i in range(10):
        time.sleep(1)
        if is_port_listening(58890):
            logger.info("wpscloudsvr 已启动 (等待了 %s 秒)", i + 1)
            return True
    logger.error("wpscloudsvr 启动超时")
    return False


def start_gui(base_path=None):
    """启动 GUI 窗口"""
    ensure_wps_cloud_service()

    qt_app = QApplication(sys.argv)
    app_icon = QIcon(_icon_path("robot.png"))
    qt_app.setWindowIcon(app_icon)
    setTheme(Theme.LIGHT, save=True, lazy=False)

    from gui.views import MainWindow

    window = MainWindow()
    tray_icon = None
    if QSystemTrayIcon.isSystemTrayAvailable():
        qt_app.setQuitOnLastWindowClosed(False)
        window.set_tray_available(True)

        tray_menu = QMenu(window)
        show_action = QAction(t("tray.show"), tray_menu)
        quit_action = QAction(t("tray.quit"), tray_menu)
        show_action.triggered.connect(window.show_from_tray)
        quit_action.triggered.connect(window.quit_from_tray)
        tray_menu.addAction(show_action)
        tray_menu.addAction(quit_action)

        tray_icon = QSystemTrayIcon(app_icon, qt_app)
        tray_icon.setToolTip(t("tray.tooltip"))
        tray_icon.setContextMenu(tray_menu)
        tray_icon.activated.connect(
            lambda reason: (
                window.show_from_tray()
                if reason
                in (
                    QSystemTrayIcon.ActivationReason.Trigger,
                    QSystemTrayIcon.ActivationReason.DoubleClick,
                )
                else None
            )
        )
        tray_icon.show()
    else:
        logger.warning("系统托盘不可用，关闭主窗口将直接退出程序")

    window.show()

    qt_app.exec()


if __name__ == "__main__":
    start_gui()
