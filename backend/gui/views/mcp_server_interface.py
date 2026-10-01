"""MCP server controls and recently active client display."""

import json

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, CaptionLabel, CardWidget, InfoBar, InfoBarPosition, PushButton, SubtitleLabel

from app.core.config import settings
from app.services.mcp_runtime import runtime
from gui.i18n import subscribe_locale_changed, t, unsubscribe_locale_changed


class McpServerInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("mcpServerInterface")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(12)

        self._title = SubtitleLabel("", self)
        layout.addWidget(self._title)
        self._subtitle = CaptionLabel("", self)
        self._subtitle.setTextColor(QColor("#888888"), QColor("#aaaaaa"))
        layout.addWidget(self._subtitle)

        card = CardWidget(self)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(12)

        self._endpoint = BodyLabel("", card)
        self._endpoint.setTextInteractionFlags(Qt.TextSelectableByMouse)
        card_layout.addWidget(self._endpoint)

        self._status = BodyLabel("", card)
        card_layout.addWidget(self._status)

        actions = QHBoxLayout()
        self._start = PushButton("", card)
        self._start.clicked.connect(self._start_server)
        actions.addWidget(self._start)
        self._stop = PushButton("", card)
        self._stop.clicked.connect(self._stop_server)
        actions.addWidget(self._stop)
        actions.addStretch()
        card_layout.addLayout(actions)

        self._config_title = BodyLabel("", card)
        card_layout.addWidget(self._config_title)
        self._config = BodyLabel("", card)
        self._config.setFont(QFont("Consolas, Menlo, monospace", 10))
        self._config.setTextInteractionFlags(Qt.TextSelectableByMouse)
        card_layout.addWidget(self._config)

        self._clients_title = BodyLabel("", card)
        card_layout.addWidget(self._clients_title)
        self._clients = BodyLabel("", card)
        self._clients.setWordWrap(True)
        card_layout.addWidget(self._clients)
        self._activity_hint = CaptionLabel("", card)
        self._activity_hint.setWordWrap(True)
        self._activity_hint.setTextColor(QColor("#888888"), QColor("#aaaaaa"))
        card_layout.addWidget(self._activity_hint)

        layout.addWidget(card)
        layout.addStretch()

        self._timer = QTimer(self)
        self._timer.setInterval(2000)
        self._timer.timeout.connect(self._refresh)
        self._timer.start()
        subscribe_locale_changed(self._retranslate)
        self.destroyed.connect(lambda: unsubscribe_locale_changed(self._retranslate))
        self._retranslate()

    def _endpoint_url(self) -> str:
        host = settings.HOST
        if host in {"0.0.0.0", "::"}:
            host = "127.0.0.1"
        if ":" in host and not host.startswith("["):
            host = f"[{host}]"
        return f"http://{host}:{settings.PORT}/mcp/"

    def _start_server(self):
        if not runtime.start():
            InfoBar.error(
                title=t("mcp.startFailed"),
                content=t("mcp.backendUnavailable"),
                parent=self,
                position=InfoBarPosition.TOP,
                duration=4000,
            )
        self._refresh()

    def _stop_server(self):
        runtime.stop()
        self._refresh()

    def _refresh(self):
        state = runtime.snapshot()
        running = state["running"]
        ready = state["ready"]
        if running:
            self._status.setText(t("mcp.running"))
            self._status.setStyleSheet("color: #16a34a;")
        elif ready:
            self._status.setText(t("mcp.stopped"))
            self._status.setStyleSheet("color: #d97706;")
        else:
            self._status.setText(t("mcp.backendUnavailable"))
            self._status.setStyleSheet("color: #dc2626;")
        self._start.setEnabled(ready and not running)
        self._stop.setEnabled(running)

        clients = state["clients"] if running else []
        self._clients_title.setText(t("mcp.clients", count=len(clients)))
        if clients:
            self._clients.setText("\n".join(
                t("mcp.client", name=item["name"], seconds=item["seconds_ago"])
                for item in clients
            ))
        else:
            self._clients.setText(t("mcp.noClients"))

    def _retranslate(self, _locale: str = ""):
        self._title.setText(t("mcp.title"))
        self._subtitle.setText(t("mcp.subtitle"))
        self._endpoint.setText(t("mcp.endpoint", url=self._endpoint_url()))
        self._start.setText(t("mcp.start"))
        self._stop.setText(t("mcp.stop"))
        self._config_title.setText(t("mcp.configTitle"))
        self._config.setText(json.dumps(
            {"mcpServers": {"wordagent": {"url": self._endpoint_url()}}}, indent=2,
        ))
        self._activity_hint.setText(t("mcp.activityHint"))
        self._refresh()
