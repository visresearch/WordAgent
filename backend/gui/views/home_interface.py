"""主页界面 - 使用 qfluentwidgets 组件 + QWidget 基类"""

import os
import webbrowser

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon
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
    IconWidget,
    FluentIcon,
    InfoBadge,
    PushButton,
)


class _InfoCard(CardWidget):
    """功能信息卡片"""

    def __init__(self, icon: FluentIcon, title: str, desc: str, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(112)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        icon_widget = IconWidget(icon, self)
        icon_widget.setFixedSize(20, 20)
        layout.addWidget(icon_widget, alignment=Qt.AlignVCenter)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        t = StrongBodyLabel(title, self)
        d = CaptionLabel(desc, self)
        d.setTextColor(QColor("#888888"), QColor("#aaaaaa"))
        d.setWordWrap(True)

        text_layout.addWidget(t)
        text_layout.addWidget(d)
        layout.addLayout(text_layout, 1)


class HomeInterface(QWidget):
    """主页界面"""

    GITHUB_URL = "https://github.com/visresearch/WordAgent"
    WEBSITE_URL = "https://visresearch.github.io/WordAgent/"

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
        subtitle = CaptionLabel("让写作有策略，让表达更智能", self)
        subtitle.setTextColor(QColor("#888888"), QColor("#aaaaaa"))
        title_col.addWidget(title)
        title_col.addWidget(subtitle)

        button_row = QHBoxLayout()
        button_row.setSpacing(10)

        github_button = PushButton("GitHub", self)
        github_icon_path = os.path.join(os.path.dirname(__file__), "..", "resources", "icon", "github.svg")
        github_icon_path = os.path.normpath(github_icon_path)
        if os.path.exists(github_icon_path):
            github_button.setIcon(QIcon(github_icon_path))
        github_button.clicked.connect(lambda: self._open_url(self.GITHUB_URL))
        button_row.addWidget(github_button)

        website_button = PushButton("官网", self)
        website_icon_path = os.path.join(os.path.dirname(__file__), "..", "resources", "icon", "Web.svg")
        website_icon_path = os.path.normpath(website_icon_path)
        if os.path.exists(website_icon_path):
            website_button.setIcon(QIcon(website_icon_path))
        website_button.clicked.connect(lambda: self._open_url(self.WEBSITE_URL))
        button_row.addWidget(website_button)
        button_row.addStretch(1)

        title_col.addSpacing(8)
        title_col.addLayout(button_row)
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
        row1.addWidget(
            _InfoCard(
                FluentIcon.APPLICATION,
                "跨平台适配",
                "以 WPS 和 Microsoft Word 为载体，同时支持 Windows 和 Linux，让用户低门槛获得 AI 写作辅助体验。",
                self,
            )
        )
        row1.addWidget(
            _InfoCard(
                FluentIcon.DOCUMENT,
                "原生富文本生成",
                "智能体理解 Word 文档结构，支持标题、正文、加粗、字体、缩进、行距等样式生成与编辑。",
                self,
            )
        )
        layout.addLayout(row1)
        layout.addSpacing(16)

        row2 = QHBoxLayout()
        row2.setSpacing(16)
        row2.addWidget(
            _InfoCard(
                FluentIcon.CHAT,
                "多智能体协作",
                "研究员、大纲师、写手、审阅者等多智能体分工协作，面向长文写作提供更有深度的内容生成。",
                self,
            )
        )
        row2.addWidget(
            _InfoCard(
                FluentIcon.SETTING,
                "自由开放",
                "支持自定义 API 或本地服务，兼容多数主流 LLM 服务商，模型选择更灵活。",
                self,
            )
        )
        layout.addLayout(row2)

        layout.addStretch(1)

    def _open_url(self, url: str):
        webbrowser.open(url)
