"""
AI 对话界面 - 类似 ChatGPT 的对话界面
"""

from PySide6.QtCore import Qt, Signal, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QSizePolicy, QSpacerItem, QScrollArea
from PySide6.QtGui import QFont, QColor

from qfluentwidgets import (
    ScrollArea,
    TextEdit,
    PrimaryPushButton,
    TransparentPushButton,
    CardWidget,
    BodyLabel,
    SubtitleLabel,
    TitleLabel,
    ToolButton,
    FluentIcon as FIF,
    IconWidget,
    SmoothScrollArea,
    LineEdit,
    PlainTextEdit,
    PushButton,
    ProgressRing,
    InfoBar,
    InfoBarPosition,
)

import datetime


class MessageBubble(CardWidget):
    """消息气泡组件"""

    def __init__(self, message: str, is_user: bool = True, parent=None):
        super().__init__(parent)
        self.is_user = is_user
        self.message = message

        self.initUI()

    def initUI(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # 角色标签
        roleLayout = QHBoxLayout()
        roleLayout.setSpacing(8)

        if self.is_user:
            icon = IconWidget(FIF.PEOPLE, self)
            roleLabel = BodyLabel("你", self)
            roleLabel.setStyleSheet("color: #0078D4; font-weight: bold;")
        else:
            icon = IconWidget(FIF.ROBOT, self)
            roleLabel = BodyLabel("AI 助手", self)
            roleLabel.setStyleSheet("color: #107C10; font-weight: bold;")

        icon.setFixedSize(20, 20)

        # 时间标签
        timeLabel = BodyLabel(datetime.datetime.now().strftime("%H:%M"), self)
        timeLabel.setStyleSheet("color: gray; font-size: 12px;")

        roleLayout.addWidget(icon)
        roleLayout.addWidget(roleLabel)
        roleLayout.addStretch(1)
        roleLayout.addWidget(timeLabel)

        layout.addLayout(roleLayout)

        # 消息内容
        contentLabel = BodyLabel(self.message, self)
        contentLabel.setWordWrap(True)
        contentLabel.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(contentLabel)

        # 样式
        if self.is_user:
            self.setStyleSheet("""
                MessageBubble {
                    background-color: #E3F2FD;
                    border-radius: 12px;
                    border: 1px solid #BBDEFB;
                }
            """)
        else:
            self.setStyleSheet("""
                MessageBubble {
                    background-color: #F5F5F5;
                    border-radius: 12px;
                    border: 1px solid #E0E0E0;
                }
            """)


class WelcomeWidget(QWidget):
    """欢迎界面"""

    suggestionClicked = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 60, 40, 40)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignCenter)

        # Logo/图标
        iconWidget = IconWidget(FIF.ROBOT, self)
        iconWidget.setFixedSize(64, 64)

        # 标题
        titleLabel = TitleLabel("WenCe AI", self)
        titleLabel.setAlignment(Qt.AlignCenter)

        # 副标题
        subtitleLabel = SubtitleLabel("智能写作助手", self)
        subtitleLabel.setAlignment(Qt.AlignCenter)
        subtitleLabel.setStyleSheet("color: gray;")

        # 描述
        descLabel = BodyLabel("我可以帮助你进行文档写作、内容优化、提供写作建议等", self)
        descLabel.setAlignment(Qt.AlignCenter)
        descLabel.setWordWrap(True)

        layout.addStretch(1)
        layout.addWidget(iconWidget, 0, Qt.AlignCenter)
        layout.addWidget(titleLabel)
        layout.addWidget(subtitleLabel)
        layout.addSpacing(20)
        layout.addWidget(descLabel)
        layout.addSpacing(30)

        # 建议卡片
        suggestionsLayout = QHBoxLayout()
        suggestionsLayout.setSpacing(12)

        suggestions = [
            ("帮我写一篇文章", FIF.EDIT),
            ("优化这段文字", FIF.SYNC),
            ("生成工作总结", FIF.DOCUMENT),
        ]

        for text, icon in suggestions:
            card = self.createSuggestionCard(text, icon)
            suggestionsLayout.addWidget(card)

        layout.addLayout(suggestionsLayout)
        layout.addStretch(2)

    def createSuggestionCard(self, text: str, icon) -> CardWidget:
        """创建建议卡片"""
        card = CardWidget(self)
        card.setFixedSize(180, 80)
        card.setCursor(Qt.PointingHandCursor)

        cardLayout = QVBoxLayout(card)
        cardLayout.setContentsMargins(16, 12, 16, 12)
        cardLayout.setSpacing(8)

        iconWidget = IconWidget(icon, card)
        iconWidget.setFixedSize(24, 24)

        label = BodyLabel(text, card)
        label.setWordWrap(True)

        cardLayout.addWidget(iconWidget)
        cardLayout.addWidget(label)

        # 点击事件
        card.mousePressEvent = lambda e: self.suggestionClicked.emit(text)

        return card


class ChatInterface(QWidget):
    """聊天界面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("chatInterface")
        self.messages = []
        self.isWaiting = False

        self.initUI()
        self.connectSignals()

    def initUI(self):
        """初始化UI"""
        mainLayout = QVBoxLayout(self)
        mainLayout.setContentsMargins(0, 0, 0, 0)
        mainLayout.setSpacing(0)

        # 聊天区域容器
        self.chatContainer = QWidget(self)
        chatLayout = QVBoxLayout(self.chatContainer)
        chatLayout.setContentsMargins(0, 0, 0, 0)
        chatLayout.setSpacing(0)

        # 欢迎界面
        self.welcomeWidget = WelcomeWidget(self)

        # 消息滚动区域
        self.scrollArea = SmoothScrollArea(self)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scrollArea.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        # 消息容器
        self.messageContainer = QWidget()
        self.messageContainer.setStyleSheet("background: transparent;")
        self.messageLayout = QVBoxLayout(self.messageContainer)
        self.messageLayout.setContentsMargins(40, 20, 40, 20)
        self.messageLayout.setSpacing(16)
        self.messageLayout.addStretch(1)

        self.scrollArea.setWidget(self.messageContainer)
        self.scrollArea.hide()  # 初始隐藏

        chatLayout.addWidget(self.welcomeWidget)
        chatLayout.addWidget(self.scrollArea)

        mainLayout.addWidget(self.chatContainer, 1)

        # 输入区域
        inputContainer = QWidget(self)
        inputContainer.setFixedHeight(120)
        inputContainer.setStyleSheet("""
            QWidget {
                background-color: #FAFAFA;
                border-top: 1px solid #E0E0E0;
            }
        """)

        inputLayout = QVBoxLayout(inputContainer)
        inputLayout.setContentsMargins(40, 16, 40, 16)
        inputLayout.setSpacing(12)

        # 输入框和按钮
        inputRow = QHBoxLayout()
        inputRow.setSpacing(12)

        self.inputEdit = PlainTextEdit(self)
        self.inputEdit.setPlaceholderText("输入消息，按 Enter 发送，Shift+Enter 换行...")
        self.inputEdit.setFixedHeight(60)
        self.inputEdit.setStyleSheet("""
            PlainTextEdit {
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                padding: 8px 12px;
                background-color: white;
                font-size: 14px;
            }
            PlainTextEdit:focus {
                border: 2px solid #0078D4;
            }
        """)

        # 按钮区域
        buttonLayout = QVBoxLayout()
        buttonLayout.setSpacing(8)

        self.sendButton = PrimaryPushButton("发送", self, FIF.SEND)
        self.sendButton.setFixedSize(80, 36)

        self.clearButton = TransparentPushButton("清空", self, FIF.DELETE)
        self.clearButton.setFixedSize(80, 36)

        buttonLayout.addWidget(self.sendButton)
        buttonLayout.addWidget(self.clearButton)

        inputRow.addWidget(self.inputEdit, 1)
        inputRow.addLayout(buttonLayout)

        # 提示文字
        tipLabel = BodyLabel("WenCe AI 可能会犯错，请核查重要信息。", self)
        tipLabel.setStyleSheet("color: gray; font-size: 12px;")
        tipLabel.setAlignment(Qt.AlignCenter)

        inputLayout.addLayout(inputRow)
        inputLayout.addWidget(tipLabel)

        mainLayout.addWidget(inputContainer)

        # 加载动画
        self.loadingRing = ProgressRing(self)
        self.loadingRing.setFixedSize(30, 30)
        self.loadingRing.hide()

    def connectSignals(self):
        """连接信号"""
        self.sendButton.clicked.connect(self.sendMessage)
        self.clearButton.clicked.connect(self.clearChat)
        self.welcomeWidget.suggestionClicked.connect(self.onSuggestionClicked)

        # 输入框回车发送
        self.inputEdit.textChanged.connect(self.onTextChanged)

    def onTextChanged(self):
        """文本变化时检查是否按下回车"""
        text = self.inputEdit.toPlainText()
        if text.endswith("\n") and not text.endswith("\n\n"):
            # 检查是否是 Shift+Enter（换行）
            from PySide6.QtWidgets import QApplication

            modifiers = QApplication.keyboardModifiers()
            if modifiers != Qt.ShiftModifier:
                # 移除最后的换行符并发送
                self.inputEdit.setPlainText(text.rstrip("\n"))
                cursor = self.inputEdit.textCursor()
                cursor.movePosition(cursor.End)
                self.inputEdit.setTextCursor(cursor)
                self.sendMessage()

    def onSuggestionClicked(self, text: str):
        """点击建议"""
        self.inputEdit.setPlainText(text)
        self.sendMessage()

    def sendMessage(self):
        """发送消息"""
        text = self.inputEdit.toPlainText().strip()
        if not text or self.isWaiting:
            return

        # 隐藏欢迎界面，显示聊天区域
        if self.welcomeWidget.isVisible():
            self.welcomeWidget.hide()
            self.scrollArea.show()

        # 添加用户消息
        self.addMessage(text, is_user=True)
        self.inputEdit.clear()

        # 模拟 AI 回复
        self.isWaiting = True
        self.sendButton.setEnabled(False)

        # 模拟延迟后回复
        QTimer.singleShot(1000, lambda: self.receiveAIResponse(text))

    def receiveAIResponse(self, userMessage: str):
        """接收 AI 回复（模拟）"""
        # 这里可以接入实际的 API
        responses = {
            "帮我写一篇文章": "好的，我可以帮您写文章。请告诉我：\n\n1. 文章的主题是什么？\n2. 大约需要多少字？\n3. 文章的风格和目标读者是什么？\n\n提供这些信息后，我会为您撰写一篇高质量的文章。",
            "优化这段文字": "请将您需要优化的文字发送给我，我会帮您：\n\n• 改善语言表达\n• 调整句式结构\n• 增强文章逻辑性\n• 提升整体可读性",
            "生成工作总结": "我来帮您生成工作总结。请提供以下信息：\n\n1. 总结的时间周期（周/月/季度/年）\n2. 您的主要工作内容\n3. 重点项目和成果\n4. 遇到的问题和解决方案\n\n我会根据这些信息为您生成专业的工作总结。",
        }

        response = responses.get(
            userMessage,
            f"收到您的消息：「{userMessage}」\n\n我是 WenCe AI 写作助手，可以帮助您：\n• 撰写各类文档\n• 优化文字表达\n• 提供写作建议\n• 生成内容大纲\n\n请告诉我您需要什么帮助？",
        )

        self.addMessage(response, is_user=False)

        self.isWaiting = False
        self.sendButton.setEnabled(True)

    def addMessage(self, text: str, is_user: bool = True):
        """添加消息到聊天区域"""
        bubble = MessageBubble(text, is_user, self.messageContainer)

        # 插入到 stretch 之前
        self.messageLayout.insertWidget(self.messageLayout.count() - 1, bubble)
        self.messages.append(bubble)

        # 滚动到底部
        QTimer.singleShot(100, self.scrollToBottom)

    def scrollToBottom(self):
        """滚动到底部"""
        scrollBar = self.scrollArea.verticalScrollBar()
        scrollBar.setValue(scrollBar.maximum())

    def clearChat(self):
        """清空聊天"""
        # 清空消息
        for msg in self.messages:
            msg.deleteLater()
        self.messages.clear()

        # 显示欢迎界面
        self.scrollArea.hide()
        self.welcomeWidget.show()

        InfoBar.success(
            title="已清空", content="对话历史已清空", parent=self, position=InfoBarPosition.TOP, duration=2000
        )
