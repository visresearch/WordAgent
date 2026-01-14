"""
样式表管理
"""

from enum import Enum
from qfluentwidgets import StyleSheetBase, Theme, qconfig


class StyleSheet(StyleSheetBase, Enum):
    """样式表枚举"""

    CHAT_INTERFACE = "chat_interface"
    HOME_INTERFACE = "home_interface"
    SETTING_INTERFACE = "setting_interface"

    def path(self, theme=Theme.AUTO):
        theme = qconfig.theme if theme == Theme.AUTO else theme
        return f":/gui/resources/qss/{theme.value.lower()}/{self.value}.qss"
