"""主页界面 - 使用 qfluentwidgets 组件 + QWidget 基类"""

import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
)
from PySide6.QtSvgWidgets import QSvgWidget
from qfluentwidgets import (
    TitleLabel,
    CaptionLabel,
    BodyLabel,
    StrongBodyLabel,
    CardWidget,
    IconInfoBadge,
    FluentIcon,
    InfoBadge,
)


class _InfoCard(CardWidget):
    """功能信息卡片"""

    def __init__(self, icon: FluentIcon, title: str, desc: str, parent=None):
        super().__init__(parent)
        self.setFixedHeight(80)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        icon_widget = IconInfoBadge.info(icon, self)
        icon_widget.setFixedSize(36, 36)
        layout.addWidget(icon_widget, alignment=Qt.AlignVCenter)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        t = StrongBodyLabel(title, self)
        d = CaptionLabel(desc, self)
        d.setTextColor(QColor("#888888"), QColor("#aaaaaa"))

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
        title = TitleLabel("WenCe AI", self)
        subtitle = CaptionLabel("智能写作助手，让创作更简单", self)
        subtitle.setTextColor(QColor("#888888"), QColor("#aaaaaa"))
        title_col.addWidget(title)
        title_col.addWidget(subtitle)
        header.addLayout(title_col, 1)

        layout.addLayout(header)
        layout.addSpacing(28)

        # --- 状态栏 ---
        status = CardWidget(self)
        sl = QHBoxLayout(status)
        sl.setContentsMargins(16, 12, 16, 12)
        sl.setSpacing(10)

        self._dot = InfoBadge.success("", self)
        self._dot.setFixedSize(10, 10)
        sl.addWidget(self._dot, alignment=Qt.AlignVCenter)

        self._status_label = BodyLabel("后端服务运行中", self)
        sl.addWidget(self._status_label, 1)

        self._version_label = CaptionLabel("v0.2.0", self)
        self._version_label.setTextColor(QColor("#888888"), QColor("#aaaaaa"))
        sl.addWidget(self._version_label, alignment=Qt.AlignVCenter)

        layout.addWidget(status)
        layout.addSpacing(20)

        # --- 功能卡片 ---
        row1 = QHBoxLayout()
        row1.setSpacing(16)
        row1.addWidget(_InfoCard(FluentIcon.EDIT, "AI 校对", "智能检查文档中的错误并给出修改建议", self))
        row1.addWidget(_InfoCard(FluentIcon.CHAT, "AI 对话", "与 AI 助手自由对话，获取写作灵感", self))
        layout.addLayout(row1)
        layout.addSpacing(16)

        row2 = QHBoxLayout()
        row2.setSpacing(16)
        row2.addWidget(_InfoCard(FluentIcon.DOCUMENT, "全文润色", "一键优化文档的表达和结构", self))
        row2.addWidget(_InfoCard(FluentIcon.APPLICATION, "插件管理", "安装和管理 WPS Office 加载项", self))
        layout.addLayout(row2)

        layout.addStretch(1)
