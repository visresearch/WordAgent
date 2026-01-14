"""
WenCe AI GUI - 主入口文件
使用 PySide6 和 PyQt-Fluent-Widgets
"""

import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

from qfluentwidgets import setTheme, Theme, setThemeColor

from .views.main_window import MainWindow


def main():
    # 启用高DPI缩放
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)

    # 设置主题
    setTheme(Theme.AUTO)
    setThemeColor("#0078D4")  # 微软蓝色

    # 创建主窗口
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
