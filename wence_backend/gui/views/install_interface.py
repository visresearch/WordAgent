"""安装界面 - 使用 qfluentwidgets 组件 + QWidget 基类，内嵌 WebEngine"""

from PySide6.QtCore import QUrl
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtWebEngineWidgets import QWebEngineView
from qfluentwidgets import SubtitleLabel, CaptionLabel, CardWidget


class InstallInterface(QWidget):
    """安装管理界面 - 内嵌 WebEngine"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("installInterface")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(12)

        # --- 标题栏 ---
        title = SubtitleLabel("安装管理", self)
        layout.addWidget(title)

        subtitle = CaptionLabel("管理 WPS Office 加载项的安装与卸载", self)
        subtitle.setTextColor(QColor("#888888"), QColor("#aaaaaa"))
        layout.addWidget(subtitle)

        # --- WebEngine（包裹在 CardWidget 中） ---
        card = CardWidget(self)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(2, 2, 2, 2)

        self._webview = QWebEngineView(card)
        card_layout.addWidget(self._webview)
        layout.addWidget(card, 1)

        from app.core.config import settings as app_settings

        url = f"http://{app_settings.HOST}:{app_settings.PORT}/publish"
        self._webview.setUrl(QUrl(url))
