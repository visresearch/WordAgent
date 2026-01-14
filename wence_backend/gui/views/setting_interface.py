"""
设置界面
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtGui import QColor

from qfluentwidgets import (
    ScrollArea,
    ExpandLayout,
    SettingCardGroup,
    SwitchSettingCard,
    OptionsSettingCard,
    PushSettingCard,
    PrimaryPushSettingCard,
    HyperlinkCard,
    ComboBoxSettingCard,
    setTheme,
    Theme,
    setThemeColor,
    FluentIcon as FIF,
    TitleLabel,
    BodyLabel,
    InfoBar,
    InfoBarPosition,
    ColorPickerButton,
    CustomColorSettingCard,
)

from ..common.config import cfg


class SettingInterface(ScrollArea):
    """设置界面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("settingInterface")

        # 容器
        self.scrollWidget = QWidget(self)
        self.expandLayout = ExpandLayout(self.scrollWidget)

        # 标题
        self.settingLabel = TitleLabel("设置", self.scrollWidget)

        # 初始化设置组
        self.initSettingCards()
        self.initLayout()

    def initSettingCards(self):
        """初始化设置卡片"""
        # 个性化设置组
        self.personalGroup = SettingCardGroup("个性化", self.scrollWidget)

        self.themeCard = OptionsSettingCard(
            cfg.themeMode,
            FIF.BRUSH,
            "应用主题",
            "调整应用的外观主题",
            texts=["浅色", "深色", "跟随系统"],
            parent=self.personalGroup,
        )

        # 主题颜色选择
        self.themeColorCard = CustomColorSettingCard(
            cfg.themeColor, FIF.PALETTE, "主题颜色", "自定义应用的主题色调", parent=self.personalGroup
        )

        # API 设置组
        self.apiGroup = SettingCardGroup("API 设置", self.scrollWidget)

        self.apiUrlCard = PushSettingCard(
            "配置", FIF.LINK, "API 地址", f"当前: {cfg.get(cfg.apiBaseUrl)}", self.apiGroup
        )

        # 聊天设置组
        self.chatGroup = SettingCardGroup("聊天设置", self.scrollWidget)

        self.markdownCard = SwitchSettingCard(
            FIF.EDIT, "Markdown 渲染", "启用后将渲染 AI 回复中的 Markdown 格式", cfg.enableMarkdown, self.chatGroup
        )

        self.autoScrollCard = SwitchSettingCard(
            FIF.SCROLL, "自动滚动", "新消息时自动滚动到底部", cfg.enableAutoScroll, self.chatGroup
        )

        # 关于
        self.aboutGroup = SettingCardGroup("关于", self.scrollWidget)

        self.aboutCard = PrimaryPushSettingCard(
            "关于", FIF.INFO, "WenCe AI", "版本 0.1.0 - 智能写作助手", self.aboutGroup
        )

        self.feedbackCard = HyperlinkCard(
            "https://github.com", "打开 GitHub", FIF.GITHUB, "反馈问题", "在 GitHub 上提交问题或建议", self.aboutGroup
        )

        # 添加卡片到组
        self.personalGroup.addSettingCard(self.themeCard)
        self.personalGroup.addSettingCard(self.themeColorCard)
        self.apiGroup.addSettingCard(self.apiUrlCard)
        self.chatGroup.addSettingCard(self.markdownCard)
        self.chatGroup.addSettingCard(self.autoScrollCard)
        self.aboutGroup.addSettingCard(self.aboutCard)
        self.aboutGroup.addSettingCard(self.feedbackCard)

        # 连接信号
        self.themeCard.optionChanged.connect(self.onThemeChanged)
        self.themeColorCard.colorChanged.connect(self.onThemeColorChanged)
        self.aboutCard.clicked.connect(self.showAboutInfo)

    def initLayout(self):
        """初始化布局"""
        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # 添加组件到布局
        self.expandLayout.setContentsMargins(36, 20, 36, 36)
        self.expandLayout.setSpacing(28)

        self.expandLayout.addWidget(self.settingLabel)
        self.expandLayout.addWidget(self.personalGroup)
        self.expandLayout.addWidget(self.apiGroup)
        self.expandLayout.addWidget(self.chatGroup)
        self.expandLayout.addWidget(self.aboutGroup)

        # 样式
        self.scrollWidget.setStyleSheet("background: transparent;")

    def onThemeChanged(self, index):
        """主题变化"""
        # index: 0=浅色, 1=深色, 2=跟随系统
        theme_map = {0: Theme.LIGHT, 1: Theme.DARK, 2: Theme.AUTO}
        theme = theme_map.get(index, Theme.AUTO)
        setTheme(theme)
        InfoBar.success(
            title="主题已更换",
            content=f"主题已切换为：{['浅色', '深色', '跟随系统'][index]}",
            parent=self,
            position=InfoBarPosition.TOP,
            duration=2000,
        )

    def onThemeColorChanged(self, color):
        """主题颜色变化"""
        setThemeColor(color)
        InfoBar.success(
            title="主题颜色已更新",
            content=f"新的主题色：{color.name()}",
            parent=self,
            position=InfoBarPosition.TOP,
            duration=2000,
        )

    def showAboutInfo(self):
        """显示关于信息"""
        InfoBar.info(
            title="WenCe AI",
            content="版本 0.1.0\n智能写作助手，让创作更简单。",
            parent=self,
            position=InfoBarPosition.TOP,
            duration=3000,
        )
