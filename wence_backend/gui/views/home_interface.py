"""主页界面 - 纯 PySide6"""

import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPainter, QBrush, QColor
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
)
from PySide6.QtSvgWidgets import QSvgWidget


class _StatusDot(QWidget):
    """小圆点状态指示器"""

    def __init__(self, color="#4CAF50", parent=None):
        super().__init__(parent)
        self.setFixedSize(10, 10)
        self._color = color

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QBrush(QColor(self._color)))
        p.setPen(Qt.NoPen)
        p.drawEllipse(0, 0, 10, 10)
        p.end()


class _InfoCard(QFrame):
    """简单信息卡片"""

    def __init__(self, emoji: str, title: str, desc: str, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setFixedHeight(80)
        self.setStyleSheet(
            """
            QFrame {
                background: #f9f9fb;
                border: 1px solid #e8e8e8;
                border-radius: 8px;
            }
            """
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        icon_label = QLabel(emoji, self)
        icon_label.setFont(QFont("", 22))
        icon_label.setFixedWidth(36)
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        t = QLabel(title, self)
        t.setFont(QFont("", 13, QFont.Weight.DemiBold))
        d = QLabel(desc, self)
        d.setStyleSheet("color: #888; font-size: 12px;")

        text_layout.addWidget(t)
        text_layout.addWidget(d)
        layout.addLayout(text_layout, 1)


class HomeInterface(QWidget):
    """主页界面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("homeInterface")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 32, 36, 36)
        layout.setSpacing(0)

        # --- Logo + 标题 ---
        header = QHBoxLayout()
        header.setSpacing(20)

        icon_path = os.path.join(os.path.dirname(__file__), "..", "resources", "icon", "robot.svg")
        icon_path = os.path.normpath(icon_path)
        if os.path.exists(icon_path):
            svg = QSvgWidget(icon_path, self)
            svg.setFixedSize(64, 64)
            header.addWidget(svg, alignment=Qt.AlignVCenter)

        title_col = QVBoxLayout()
        title_col.setSpacing(4)
        title = QLabel("WenCe AI", self)
        title.setFont(QFont("", 22, QFont.Weight.Bold))
        subtitle = QLabel("智能写作助手，让创作更简单", self)
        subtitle.setStyleSheet("color: #888; font-size: 14px;")
        title_col.addWidget(title)
        title_col.addWidget(subtitle)
        header.addLayout(title_col, 1)

        layout.addLayout(header)
        layout.addSpacing(28)

        # --- 状态栏 ---
        status = QFrame(self)
        status.setFrameShape(QFrame.StyledPanel)
        status.setStyleSheet(
            "QFrame { background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; }"
        )
        sl = QHBoxLayout(status)
        sl.setContentsMargins(16, 12, 16, 12)
        sl.setSpacing(10)

        self._dot = _StatusDot("#4CAF50", self)
        sl.addWidget(self._dot, alignment=Qt.AlignVCenter)

        self._status_label = QLabel("后端服务运行中", self)
        self._status_label.setStyleSheet("font-size: 14px; color: #333; border: none;")
        sl.addWidget(self._status_label, 1)

        self._version_label = QLabel("v0.2.0", self)
        self._version_label.setStyleSheet("color: #888; font-size: 13px; border: none;")
        sl.addWidget(self._version_label, alignment=Qt.AlignVCenter)

        layout.addWidget(status)
        layout.addSpacing(20)

        # --- 功能卡片 ---
        row1 = QHBoxLayout()
        row1.setSpacing(16)
        row1.addWidget(_InfoCard("✏️", "AI 校对", "智能检查文档中的错误并给出修改建议", self))
        row1.addWidget(_InfoCard("💬", "AI 对话", "与 AI 助手自由对话，获取写作灵感", self))
        layout.addLayout(row1)
        layout.addSpacing(16)

        row2 = QHBoxLayout()
        row2.setSpacing(16)
        row2.addWidget(_InfoCard("📝", "全文润色", "一键优化文档的表达和结构", self))
        row2.addWidget(_InfoCard("📦", "插件管理", "安装和管理 WPS Office 加载项", self))
        layout.addLayout(row2)

        layout.addStretch(1)

