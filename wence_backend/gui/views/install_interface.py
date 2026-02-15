"""安装界面 - 纯 PySide6，直接内嵌 WebEngine 加载 /publish"""

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtWebEngineWidgets import QWebEngineView


class InstallInterface(QWidget):
    """安装管理界面 - 直接内嵌 WebEngine"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("installInterface")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- 标题栏 ---
        header = QWidget(self)
        header.setStyleSheet("background: #f7f7f8; border-bottom: 1px solid #e8e8e8;")
        hl = QVBoxLayout(header)
        hl.setContentsMargins(24, 16, 24, 12)
        hl.setSpacing(4)

        title = QLabel("📦 安装管理", self)
        title.setFont(QFont("", 18, QFont.Weight.Bold))
        hl.addWidget(title)

        subtitle = QLabel("管理 WPS Office 加载项的安装与卸载", self)
        subtitle.setStyleSheet("color: #888; font-size: 13px;")
        hl.addWidget(subtitle)

        layout.addWidget(header)

        # --- WebEngine ---
        self._webview = QWebEngineView(self)
        layout.addWidget(self._webview, 1)

        from app.core.config import settings as app_settings

        url = f"http://{app_settings.HOST}:{app_settings.PORT}/publish"
        self._webview.setUrl(QUrl(url))
