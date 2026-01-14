"""
主窗口 - 使用 Fluent Navigation
"""

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from qfluentwidgets import (
    NavigationItemPosition,
    MSFluentWindow,
    SplashScreen,
    NavigationAvatarWidget,
    qrouter,
    FluentIcon as FIF,
)

from .home_interface import HomeInterface
from .chat_interface import ChatInterface
from .setting_interface import SettingInterface


class MainWindow(MSFluentWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.initWindow()

        # 创建子界面
        self.homeInterface = HomeInterface(self)
        self.chatInterface = ChatInterface(self)
        self.settingInterface = SettingInterface(self)

        # 初始化导航
        self.initNavigation()

    def initWindow(self):
        """初始化窗口"""
        self.resize(1200, 800)
        self.setMinimumSize(800, 600)
        self.setWindowTitle("WenCe AI Writing Assistant")

        # 居中显示
        desktop = QApplication.primaryScreen().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w // 2 - self.width() // 2, h // 2 - self.height() // 2)

    def initNavigation(self):
        """初始化导航栏"""
        # 添加子界面到导航
        self.addSubInterface(self.homeInterface, FIF.HOME, "主页", position=NavigationItemPosition.TOP)

        self.addSubInterface(self.chatInterface, FIF.CHAT, "AI 对话", position=NavigationItemPosition.TOP)

        # 底部导航项
        self.addSubInterface(self.settingInterface, FIF.SETTING, "设置", position=NavigationItemPosition.BOTTOM)

        # 设置默认路由
        qrouter.setDefaultRouteKey(self.stackedWidget, self.chatInterface.objectName())

    def closeEvent(self, event):
        """关闭事件"""
        super().closeEvent(event)
