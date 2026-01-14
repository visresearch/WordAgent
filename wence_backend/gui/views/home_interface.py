"""
主页界面
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel

from qfluentwidgets import (
    ScrollArea,
    TitleLabel,
    SubtitleLabel,
    BodyLabel,
    PrimaryPushButton,
    TransparentPushButton,
    CardWidget,
    FluentIcon as FIF,
    IconWidget,
)


class BannerWidget(QWidget):
    """横幅组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(200)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 40, 36, 40)
        layout.setSpacing(16)

        # 标题
        titleLabel = TitleLabel("WenCe AI Writing Assistant", self)
        titleLabel.setStyleSheet("color: white;")

        # 副标题
        subtitleLabel = SubtitleLabel("智能写作助手，让创作更简单", self)
        subtitleLabel.setStyleSheet("color: rgba(255, 255, 255, 0.8);")

        # 按钮
        buttonLayout = QHBoxLayout()
        buttonLayout.setSpacing(12)

        startBtn = PrimaryPushButton("开始对话", self, FIF.CHAT)
        startBtn.setFixedWidth(140)

        docBtn = TransparentPushButton("查看文档", self, FIF.DOCUMENT)
        docBtn.setFixedWidth(140)
        docBtn.setStyleSheet("color: white;")

        buttonLayout.addWidget(startBtn)
        buttonLayout.addWidget(docBtn)
        buttonLayout.addStretch(1)

        layout.addWidget(titleLabel)
        layout.addWidget(subtitleLabel)
        layout.addLayout(buttonLayout)
        layout.addStretch(1)

        # 背景渐变
        self.setStyleSheet("""
            BannerWidget {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #667eea, stop:1 #764ba2
                );
                border-radius: 12px;
            }
        """)


class FeatureCard(CardWidget):
    """特性卡片"""

    def __init__(self, icon, title, content, parent=None):
        super().__init__(parent)
        self.setFixedSize(280, 160)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # 图标
        iconWidget = IconWidget(icon, self)
        iconWidget.setFixedSize(36, 36)

        # 标题
        titleLabel = SubtitleLabel(title, self)

        # 内容
        contentLabel = BodyLabel(content, self)
        contentLabel.setWordWrap(True)

        layout.addWidget(iconWidget)
        layout.addWidget(titleLabel)
        layout.addWidget(contentLabel)
        layout.addStretch(1)


class HomeInterface(ScrollArea):
    """主页界面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("homeInterface")

        # 容器
        self.view = QWidget(self)
        self.view.setObjectName("homeView")

        # 布局
        self.vBoxLayout = QVBoxLayout(self.view)
        self.vBoxLayout.setContentsMargins(36, 20, 36, 36)
        self.vBoxLayout.setSpacing(24)

        self.initWidget()

    def initWidget(self):
        """初始化组件"""
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # 横幅
        banner = BannerWidget(self)
        self.vBoxLayout.addWidget(banner)

        # 功能标题
        featureTitle = TitleLabel("功能特性", self)
        self.vBoxLayout.addWidget(featureTitle)

        # 功能卡片布局
        cardLayout = QHBoxLayout()
        cardLayout.setSpacing(16)

        # 添加功能卡片
        card1 = FeatureCard(FIF.CHAT, "智能对话", "支持多轮对话，智能理解上下文，提供专业写作建议", self)

        card2 = FeatureCard(FIF.EDIT, "文档编辑", "支持 Word 文档的智能编辑和格式优化", self)

        card3 = FeatureCard(FIF.SYNC, "实时协作", "与 Word 插件无缝集成，实时同步编辑内容", self)

        cardLayout.addWidget(card1)
        cardLayout.addWidget(card2)
        cardLayout.addWidget(card3)
        cardLayout.addStretch(1)

        self.vBoxLayout.addLayout(cardLayout)
        self.vBoxLayout.addStretch(1)

        # 样式
        self.view.setStyleSheet("""
            #homeView {
                background: transparent;
            }
        """)
