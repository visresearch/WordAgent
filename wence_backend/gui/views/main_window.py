"""
主窗口 - 纯 PySide6，左侧导航 + 右侧 StackedWidget
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QStackedWidget,
    QApplication,
)

from .home_interface import HomeInterface
from .install_interface import InstallInterface
from .console_interface import ConsoleInterface


class NavButton(QPushButton):
    """导航按钮"""

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setFixedHeight(40)
        self.setCursor(Qt.PointingHandCursor)


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

        # --- 左侧导航 ---
        nav = QWidget()
        nav.setFixedWidth(140)
        nav.setStyleSheet(
            """
            QWidget {
                background: #f7f7f8;
                border-right: 1px solid #e0e0e0;
            }
            QPushButton {
                text-align: left;
                padding: 8px 20px;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                color: #555;
                background: transparent;
                margin: 2px 8px;
            }
            QPushButton:hover {
                background: #eaeaec;
            }
            QPushButton:checked {
                background: #dde1f7;
                color: #3355cc;
                font-weight: 600;
            }
            """
        )
        nav_layout = QVBoxLayout(nav)
        nav_layout.setContentsMargins(0, 16, 0, 16)
        nav_layout.setSpacing(2)

        self._btnHome = NavButton("🏠  主页")
        self._btnInstall = NavButton("📦  安装管理")
        self._btnConsole = NavButton("🖥  终端")

        self._navButtons = [self._btnHome, self._btnInstall, self._btnConsole]
        for btn in self._navButtons:
            nav_layout.addWidget(btn)

        nav_layout.addStretch(1)
        root.addWidget(nav)

        # --- 右侧内容区 ---
        self._stack = QStackedWidget()
        self._stack.setStyleSheet("background: #ffffff;")

        self._homeInterface = HomeInterface(self)
        self._installInterface = InstallInterface(self)
        self._consoleInterface = ConsoleInterface(self)

        self._stack.addWidget(self._homeInterface)
        self._stack.addWidget(self._installInterface)
        self._stack.addWidget(self._consoleInterface)

        root.addWidget(self._stack, 1)

        # 绑定导航
        self._btnHome.clicked.connect(lambda: self._switchPage(0))
        self._btnInstall.clicked.connect(lambda: self._switchPage(1))
        self._btnConsole.clicked.connect(lambda: self._switchPage(2))

        # 默认主页
        self._switchPage(0)

    def _switchPage(self, index):
        self._stack.setCurrentIndex(index)
        for i, btn in enumerate(self._navButtons):
            btn.setChecked(i == index)
