"""主页界面"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout

from qfluentwidgets import TitleLabel, SubtitleLabel


class HomeInterface(QWidget):
    """主页界面 - 简洁标题页"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("homeInterface")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 40, 36, 36)
        layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        layout.setSpacing(16)

        title = TitleLabel("WenCe AI Writing Assistant", self)
        title.setAlignment(Qt.AlignCenter)

        subtitle = SubtitleLabel("智能写作助手，让创作更简单", self)
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #888;")

        layout.addSpacing(60)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addStretch(1)
