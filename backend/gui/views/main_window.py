"""
主窗口 - QWidget 基类 + qfluentwidgets 导航组件
"""

from PySide6.QtCore import Qt
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
    isDarkTheme,
)

from .home_interface import HomeInterface
from .install_interface import InstallInterface
from .console_interface import ConsoleInterface


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self._initWindow()
        self._initUI()

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
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # --- 左侧导航（qfluentwidgets NavigationInterface） ---
        self._nav = NavigationInterface(self, showMenuButton=False, showReturnButton=False)
        self._nav.setFixedWidth(48)  # 收起状态宽度
        self._nav.setExpandWidth(160)

        # --- 右侧内容区 ---
        self._stack = QStackedWidget()

        self._homeInterface = HomeInterface(self)
        self._installInterface = InstallInterface(self)
        self._consoleInterface = ConsoleInterface(self)

        self._stack.addWidget(self._homeInterface)
        self._stack.addWidget(self._installInterface)
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
            icon=FluentIcon.APPLICATION,
            text="安装管理",
            onClick=lambda: self._switchPage(self._installInterface),
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
