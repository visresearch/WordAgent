"""
应用配置
"""

from enum import Enum
from PySide6.QtGui import QColor
from qfluentwidgets import (
    qconfig,
    QConfig,
    ConfigItem,
    OptionsConfigItem,
    BoolValidator,
    OptionsValidator,
    Theme,
    ConfigSerializer,
    ColorConfigItem,
)


class Language(Enum):
    """语言枚举"""

    CHINESE_SIMPLIFIED = "zh_CN"
    ENGLISH = "en_US"


class LanguageSerializer(ConfigSerializer):
    """语言序列化器"""

    def serialize(self, language):
        return language.value

    def deserialize(self, value: str):
        return Language(value)


class Config(QConfig):
    """应用配置类"""

    # 主题
    themeMode = OptionsConfigItem("MainWindow", "ThemeMode", Theme.AUTO, OptionsValidator(Theme), ConfigSerializer())

    # 主题颜色
    themeColor = ColorConfigItem("MainWindow", "ThemeColor", "#0078D4")

    # 语言
    language = OptionsConfigItem(
        "MainWindow", "Language", Language.CHINESE_SIMPLIFIED, OptionsValidator(Language), LanguageSerializer()
    )

    # API 设置
    apiBaseUrl = ConfigItem("API", "BaseUrl", "http://127.0.0.1:8000")

    # 聊天设置
    enableMarkdown = ConfigItem("Chat", "EnableMarkdown", True, BoolValidator())
    enableAutoScroll = ConfigItem("Chat", "EnableAutoScroll", True, BoolValidator())


# 创建配置实例
cfg = Config()
qconfig.load("config/config.json", cfg)
