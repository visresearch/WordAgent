"""主页界面 - 使用 qfluentwidgets 组件 + QWidget 基类"""

import json
import os
import re
import threading
import webbrowser
from urllib.request import Request, urlopen

from PySide6.QtCore import Qt, QTimer, Signal
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
    InfoBar,
    InfoBarPosition,
    ComboBox,
)
from gui.i18n import get_locale, set_locale, subscribe_locale_changed, t


def check_latest_release(api_urls: tuple[str, ...], *, release_url: str) -> dict:
    """Try each API once; keep navigation on the application's release URL."""
    errors = []
    for url in api_urls:
        try:
            request = Request(
                url,
                headers={
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "WenCeAI-VersionChecker",
                },
            )
            with urlopen(request, timeout=3) as response:
                payload = json.loads(response.read().decode("utf-8"))
            tag = payload.get("tag_name") if isinstance(payload, dict) else None
            if not isinstance(tag, str) or not re.search(r"\d+(?:\.\d+)*", tag):
                raise ValueError("更新接口未返回有效版本号")
            return {"ok": True, "latest_tag": tag.strip(), "latest_url": release_url, "error": ""}
        except (OSError, ValueError) as exc:
            # Includes HTTP/URL errors, timeouts, invalid JSON and invalid UTF-8.
            errors.append(f"{url}: {exc}")

    return {"ok": False, "latest_tag": "", "latest_url": release_url, "error": "; ".join(errors)}


def _read_local_version() -> str:
    """从环境变量读取本地版本号。"""
    try:
        from app.core.config import settings

        return settings.APP_VERSION or ""
    except Exception:
        return os.environ.get("APP_VERSION") or ""


def _version_key(version: str) -> tuple[int, ...]:
    """把版本字符串转换为可比较的数字元组。"""
    normalized = version.strip()
    match = re.search(r"(\d+(?:\.\d+)*)", normalized)
    if not match:
        return tuple()
    return tuple(int(part) for part in match.group(1).split("."))


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

        self._title_label = StrongBodyLabel(title, self)
        self._desc_label = CaptionLabel(desc, self)
        self._desc_label.setTextColor(QColor("#888888"), QColor("#aaaaaa"))
        self._desc_label.setWordWrap(True)

        text_layout.addWidget(self._title_label)
        text_layout.addWidget(self._desc_label)
        layout.addLayout(text_layout, 1)

    def setTexts(self, title: str, desc: str):
        """Update card title and description (used on language change)."""
        self._title_label.setText(title)
        self._desc_label.setText(desc)


class HomeInterface(QWidget):
    """主页界面"""

    updateCheckFinished = Signal(dict)

    GITHUB_URL = "https://github.com/visresearch/WordAgent"
    GITHUB_RELEASE_API = "https://api.github.com/repos/visresearch/WordAgent/releases/latest"
    # Fallbacks apply only to update metadata, not browser or download links.
    GITHUB_RELEASE_API_URLS = (
        GITHUB_RELEASE_API,
        f"https://gh-proxy.com/{GITHUB_RELEASE_API}",
    )
    WEBSITE_URL = "https://visresearch.github.io/WordAgent/"
    RELEASE_URL = "https://github.com/visresearch/WordAgent/releases/latest"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("homeInterface")
        self._current_version = _read_local_version()
        self._update_check_result: dict | None = None
        self.updateCheckFinished.connect(self._on_update_check_finished)

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
        title = TitleLabel(t("app.name"), self)
        self._subtitle_label = subtitle = CaptionLabel(t("home.subtitle"), self)
        subtitle.setTextColor(QColor("#888888"), QColor("#aaaaaa"))
        title_col.addWidget(title)
        title_col.addWidget(subtitle)

        button_row = QHBoxLayout()
        button_row.setSpacing(10)

        github_button = PushButton(t("home.button.github"), self)
        github_icon_path = os.path.join(os.path.dirname(__file__), "..", "resources", "icon", "github.svg")
        github_icon_path = os.path.normpath(github_icon_path)
        if os.path.exists(github_icon_path):
            github_button.setIcon(QIcon(github_icon_path))
        github_button.clicked.connect(lambda: self._open_url(self.GITHUB_URL))
        button_row.addWidget(github_button)

        self._website_button = website_button = PushButton(t("home.button.website"), self)
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

        self._status_label = BodyLabel(t("home.status.runningChecking"), self)
        sl.addWidget(self._status_label, 1)

        self._version_label = CaptionLabel(
            t("home.version.current", version=self._current_version or t("home.version.unknown")), self
        )
        self._version_label.setTextColor(QColor("#888888"), QColor("#aaaaaa"))
        sl.addWidget(self._version_label, alignment=Qt.AlignVCenter)

        self._update_label = CaptionLabel(t("home.update.checking"), self)
        self._update_label.setTextColor(QColor("#888888"), QColor("#aaaaaa"))
        sl.addWidget(self._update_label, alignment=Qt.AlignVCenter)

        self._download_button = PushButton(t("home.button.downloadLatest"), self)
        self._download_button.clicked.connect(lambda: self._open_url(self.RELEASE_URL))
        self._download_button.hide()
        sl.addWidget(self._download_button, alignment=Qt.AlignVCenter)

        layout.addWidget(status)
        layout.addSpacing(20)
        # --- language picker ---
        lang_card = CardWidget(self)
        lang_layout = QHBoxLayout(lang_card)
        lang_layout.setContentsMargins(16, 12, 16, 12)
        self._lang_label = StrongBodyLabel(t("language.label"), self)
        lang_layout.addWidget(self._lang_label, alignment=Qt.AlignVCenter)
        lang_layout.addSpacing(16)
        self._lang_picker = ComboBox(self)
        # (locale, display name) — names stay in their own language on purpose.
        self._lang_items = [
            ("en-US", "English"),
            ("zh-CN", "简体中文"),
            ("id-ID", "Bahasa Indonesia"),
            ("ja-JP", "日本語"),
            ("ko-KR", "한국어"),
            ("vi-VN", "Tiếng Việt"),
        ]
        self._lang_picker.addItems([name for _, name in self._lang_items])
        self._lang_picker.setCurrentIndex(
            max(0, next((i for i, (loc, _) in enumerate(self._lang_items) if loc == get_locale()), 0))
        )
        self._lang_picker.currentIndexChanged.connect(self._on_language_changed)
        lang_layout.addWidget(self._lang_picker, alignment=Qt.AlignVCenter)
        lang_layout.addStretch(1)
        layout.addWidget(lang_card)
        layout.addSpacing(20)

        # --- 功能卡片 ---
        row1 = QHBoxLayout()
        row1.setSpacing(16)
        self._card_cross = _InfoCard(
            FluentIcon.APPLICATION,
            t("home.cards.crossPlatform.title"),
            t("home.cards.crossPlatform.desc"),
            self,
        )
        row1.addWidget(self._card_cross)
        self._card_rich = _InfoCard(
            FluentIcon.DOCUMENT,
            t("home.cards.richText.title"),
            t("home.cards.richText.desc"),
            self,
        )
        row1.addWidget(self._card_rich)
        layout.addLayout(row1)
        layout.addSpacing(16)

        row2 = QHBoxLayout()
        row2.setSpacing(16)
        self._card_workflow = _InfoCard(
            FluentIcon.CHAT,
            t("home.cards.workflow.title"),
            t("home.cards.workflow.desc"),
            self,
        )
        row2.addWidget(self._card_workflow)
        self._card_open = _InfoCard(
            FluentIcon.SETTING,
            t("home.cards.open.title"),
            t("home.cards.open.desc"),
            self,
        )
        row2.addWidget(self._card_open)
        layout.addLayout(row2)

        layout.addStretch(1)
        QTimer.singleShot(0, self._check_latest_release_async)

    def _on_language_changed(self, index: int):
        """Apply the selected interface language and refresh static texts."""
        if index < 0 or index >= len(self._lang_items):
            return
        locale, _ = self._lang_items[index]
        if locale == get_locale():
            return
        set_locale(locale)
        self._retranslate()

    def _retranslate(self):
        """Update all translatable labels on this page."""
        self._lang_label.setText(t("language.label"))
        self._subtitle_label.setText(t("home.subtitle"))
        self._website_button.setText(t("home.button.website"))
        self._version_label.setText(
            t("home.version.current", version=self._current_version or t("home.version.unknown"))
        )
        self._download_button.setText(t("home.button.downloadLatest"))
        self._render_update_status()
        self._card_cross.setTexts(t("home.cards.crossPlatform.title"), t("home.cards.crossPlatform.desc"))
        self._card_rich.setTexts(t("home.cards.richText.title"), t("home.cards.richText.desc"))
        self._card_workflow.setTexts(t("home.cards.workflow.title"), t("home.cards.workflow.desc"))
        self._card_open.setTexts(t("home.cards.open.title"), t("home.cards.open.desc"))

    def _open_url(self, url: str):
        webbrowser.open(url)

    def _check_latest_release_async(self):
        worker = threading.Thread(target=self._check_latest_release_worker, daemon=True)
        worker.start()

    def _check_latest_release_worker(self):
        result = check_latest_release(self.GITHUB_RELEASE_API_URLS, release_url=self.RELEASE_URL)
        self.updateCheckFinished.emit(result)

    def _on_update_check_finished(self, result: dict):
        self._update_check_result = result
        self._render_update_status(show_notification=True)

    def _render_update_status(self, *, show_notification: bool = False):
        """Translate the current result without restarting the check or repeating notifications."""
        result = self._update_check_result
        self._download_button.hide()
        if result is None:
            self._update_label.setText(t("home.update.checking"))
            self._update_label.setTextColor(QColor("#888888"), QColor("#aaaaaa"))
            self._status_label.setText(t("home.status.runningChecking"))
            return

        latest_tag = str(result.get("latest_tag", "")).strip()
        if not result.get("ok"):
            self._update_label.setText(t("home.update.failed"))
            self._update_label.setTextColor(QColor("#d97706"), QColor("#d97706"))
            self._status_label.setText(t("home.status.runningNoUpdateInfo"))
            return

        local_key = _version_key(self._current_version)
        latest_key = _version_key(latest_tag)
        has_new_version = bool(latest_key) and (not local_key or latest_key > local_key)

        if has_new_version:
            self._status_label.setText(t("home.status.newVersion", tag=latest_tag))
            self._update_label.setText(t("home.update.new", tag=latest_tag))
            self._update_label.setTextColor(QColor("#d97706"), QColor("#d97706"))
            self._download_button.show()
            if show_notification:
                InfoBar.warning(
                    title=t("home.infobar.newVersion.title"),
                    content=t("home.infobar.newVersion.content", tag=latest_tag),
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=5000,
                )
            return

        self._status_label.setText(t("home.status.runningLatest"))
        self._update_label.setText(t("home.update.latest"))
        self._update_label.setTextColor(QColor("#16a34a"), QColor("#16a34a"))
