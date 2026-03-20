"""
主窗口 - QWidget 基类 + qfluentwidgets 导航组件
"""

import platform
import ctypes

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QStackedWidget,
    QApplication,
)
from qfluentwidgets import (
    NavigationInterface,
    NavigationItemPosition,
    FluentIcon,
)

from .home_interface import HomeInterface
from .wps_install_interface import InstallInterface
from .office_install_interface import OfficeInstallInterface
from .console_interface import ConsoleInterface


def _icon_path(name: str) -> str:
    """获取图标文件路径"""
    from pathlib import Path

    return str(Path(__file__).parent.parent / "resources" / "icon" / name)


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self._title_bar_applied = False
        self._initWindow()
        self._initUI()

    def _set_windows_light_title_bar(self):
        if platform.system() != "Windows":
            return

        hwnd = int(self.winId())
        value = ctypes.c_int(0)
        size = ctypes.sizeof(value)
        DWMWA_USE_IMMERSIVE_DARK_MODE_NEW = 20
        DWMWA_USE_IMMERSIVE_DARK_MODE_OLD = 19

        try:
            dwmapi = ctypes.windll.dwmapi
            dwmapi.DwmSetWindowAttribute(
                hwnd,
                DWMWA_USE_IMMERSIVE_DARK_MODE_NEW,
                ctypes.byref(value),
                size,
            )
            dwmapi.DwmSetWindowAttribute(
                hwnd,
                DWMWA_USE_IMMERSIVE_DARK_MODE_OLD,
                ctypes.byref(value),
                size,
            )
        except Exception:
            pass

    def _initWindow(self):
        self.resize(900, 600)
        self.setMinimumSize(700, 500)
        self.setWindowTitle("WenCe AI")

        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            screen.width() // 2 - self.width() // 2,
            screen.height() // 2 - self.height() // 2,
        )

    def _initUI(self):
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.setStyleSheet(
            """
            QMainWindow { background-color: #f5f5f5; }
            QWidget#centralWidget { background-color: #f5f5f5; }
            """
        )

        # --- 左侧导航（qfluentwidgets NavigationInterface） ---
        self._nav = NavigationInterface(self, showMenuButton=False, showReturnButton=False)
        self._nav.setFixedWidth(48)  # 收起状态宽度
        self._nav.setExpandWidth(160)

        # --- 右侧内容区 ---
        self._stack = QStackedWidget()

        self._homeInterface = HomeInterface(self)
        self._installInterface = InstallInterface(self)
        self._officeInstallInterface = OfficeInstallInterface(self)
        self._consoleInterface = ConsoleInterface(self)

        self._stack.addWidget(self._homeInterface)
        self._stack.addWidget(self._installInterface)
        self._stack.addWidget(self._officeInstallInterface)
        self._stack.addWidget(self._consoleInterface)

        # 注册导航项
        self._nav.addItem(
            routeKey="homeInterface",
            icon=FluentIcon.HOME,
            text="主页",
            onClick=lambda: self._switchPage(self._homeInterface),
            position=NavigationItemPosition.TOP,
        )
        self._nav.addItem(
            routeKey="installInterface",
            icon=QIcon(_icon_path("WPS.svg")),
            text="WPS 加载项",
            onClick=lambda: self._switchPage(self._installInterface),
            position=NavigationItemPosition.TOP,
        )
        self._nav.addItem(
            routeKey="officeInstallInterface",
            icon=QIcon(_icon_path("Office.svg")),
            text="Office 加载项",
            onClick=lambda: self._switchPage(self._officeInstallInterface),
            position=NavigationItemPosition.TOP,
        )
        self._nav.addItem(
            routeKey="consoleInterface",
            icon=FluentIcon.COMMAND_PROMPT,
            text="终端",
            onClick=lambda: self._switchPage(self._consoleInterface),
            position=NavigationItemPosition.BOTTOM,
        )

        root.addWidget(self._nav)
        root.addWidget(self._stack, 1)

        # 默认主页
        self._switchPage(self._homeInterface)
        self._nav.setCurrentItem("homeInterface")

    def _switchPage(self, widget):
        self._stack.setCurrentWidget(widget)

    def resizeEvent(self, event):
        self._nav.setFixedHeight(self.height())
        super().resizeEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        if not self._title_bar_applied:
            self._set_windows_light_title_bar()
            self._title_bar_applied = True
