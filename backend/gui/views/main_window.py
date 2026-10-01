"""
主窗口 - QWidget 基类 + qfluentwidgets 导航组件
"""

import platform
import ctypes

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QIcon
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
from .mcp_server_interface import McpServerInterface
from .console_interface import ConsoleInterface
from .dashboard_interface import DashboardInterface
from gui.i18n import subscribe_locale_changed, t


def _icon_path(name: str) -> str:
    """获取图标文件路径"""
    from pathlib import Path

    return str(Path(__file__).parent.parent / "resources" / "icon" / name)


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self._title_bar_applied = False
        self._tray_available = False
        self._allow_close = False
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
        self.setWindowIcon(QIcon(_icon_path("robot.png")))

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
        self._dashboardInterface = DashboardInterface(self)
        self._installInterface = InstallInterface(self)
        self._officeInstallInterface = OfficeInstallInterface(self)
        self._mcpServerInterface = McpServerInterface(self)
        self._consoleInterface = ConsoleInterface(self)

        self._stack.addWidget(self._homeInterface)
        self._stack.addWidget(self._dashboardInterface)
        self._stack.addWidget(self._installInterface)
        self._stack.addWidget(self._officeInstallInterface)
        self._stack.addWidget(self._mcpServerInterface)
        self._stack.addWidget(self._consoleInterface)

        # 注册导航项
        self._nav.addItem(
            routeKey="homeInterface",
            icon=FluentIcon.HOME,
            text=t("nav.home"),
            tooltip=t("nav.home"),
            onClick=lambda: self._switchPage(self._homeInterface),
            position=NavigationItemPosition.TOP,
        )
        self._nav.addItem(
            routeKey="dashboardInterface",
            icon=QIcon(_icon_path("dashboard.svg")),
            text=t("nav.dashboard"),
            tooltip=t("nav.dashboard"),
            onClick=lambda: self._switchPage(self._dashboardInterface),
            position=NavigationItemPosition.BOTTOM,
        )
        self._nav.addItem(
            routeKey="installInterface",
            icon=QIcon(_icon_path("WPS.svg")),
            text=t("nav.wps"),
            tooltip=t("nav.wps"),
            onClick=lambda: self._switchPage(self._installInterface),
            position=NavigationItemPosition.TOP,
        )
        self._nav.addItem(
            routeKey="officeInstallInterface",
            icon=QIcon(_icon_path("Office.svg")),
            text=t("nav.office"),
            tooltip=t("nav.office"),
            onClick=lambda: self._switchPage(self._officeInstallInterface),
            position=NavigationItemPosition.TOP,
        )
        self._nav.addItem(
            routeKey="mcpServerInterface",
            icon=QIcon(_icon_path("mcp-server.svg")),
            text=t("nav.mcp"),
            tooltip=t("nav.mcp"),
            onClick=lambda: self._switchPage(self._mcpServerInterface),
            position=NavigationItemPosition.TOP,
        )
        self._nav.addItem(
            routeKey="consoleInterface",
            icon=FluentIcon.COMMAND_PROMPT,
            text=t("nav.console"),
            tooltip=t("nav.console"),
            onClick=lambda: self._switchPage(self._consoleInterface),
            position=NavigationItemPosition.BOTTOM,
        )

        root.addWidget(self._nav)
        root.addWidget(self._stack, 1)

        # 默认主页
        self._switchPage(self._homeInterface)
        self._nav.setCurrentItem("homeInterface")
        # 语言切换时刷新导航文案
        subscribe_locale_changed(self._retranslate_nav)

    def _retranslate_nav(self, _locale: str = ""):
        """Update navigation item texts after an interface language change."""
        labels = {
            "homeInterface": t("nav.home"),
            "dashboardInterface": t("nav.dashboard"),
            "installInterface": t("nav.wps"),
            "officeInstallInterface": t("nav.office"),
            "mcpServerInterface": t("nav.mcp"),
            "consoleInterface": t("nav.console"),
        }
        for key, text in labels.items():
            item = self._nav.widget(key)
            item.setText(text)
            item.setToolTip(text)

    def _switchPage(self, widget):
        self._stack.setCurrentWidget(widget)

    def set_tray_available(self, available: bool):
        """设置是否启用托盘关闭行为。"""
        self._tray_available = available

    def show_from_tray(self):
        """从系统托盘恢复主窗口。"""
        if self.isMinimized():
            self.setWindowState(self.windowState() & ~Qt.WindowMinimized)
        self.show()
        self.raise_()
        self.activateWindow()

    def quit_from_tray(self):
        """通过托盘菜单退出应用。"""
        self._allow_close = True
        self.close()
        app = QApplication.instance()
        if app is not None:
            app.quit()

    def resizeEvent(self, event):
        self._nav.setFixedHeight(self.height())
        super().resizeEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        if not self._title_bar_applied:
            self._set_windows_light_title_bar()
            self._title_bar_applied = True

    def closeEvent(self, event: QCloseEvent):
        if self._tray_available and not self._allow_close:
            event.ignore()
            self.hide()
            return
        super().closeEvent(event)
