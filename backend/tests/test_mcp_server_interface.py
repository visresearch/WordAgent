"""The MCP panel reflects the shared server state and reported client name."""

import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from app.services.mcp_runtime import McpRuntime, runtime
from gui.views.mcp_server_interface import McpServerInterface


def test_panel_starts_stops_and_displays_client():
    app = QApplication.instance() or QApplication([])
    runtime.set_ready(True)
    panel = McpServerInterface()
    try:
        assert panel._start.isEnabled()
        panel._start.click()
        assert runtime.enabled()
        runtime.seen("127.0.0.1", "codex/1.0", "Codex")
        panel._refresh()
        assert "Codex" in panel._clients.text()
        assert not panel._start.isEnabled()
        panel._stop.click()
        assert not runtime.enabled()
        assert runtime.snapshot()["clients"] == []
        assert panel._start.isEnabled()
    finally:
        panel.close()
        panel.deleteLater()
        app.processEvents()
        runtime.set_ready(False)


def test_inactive_clients_expire(monkeypatch):
    current = [1000.0]
    monkeypatch.setattr("app.services.mcp_runtime.time.monotonic", lambda: current[0])
    state = McpRuntime()
    state.set_ready(True)
    assert state.start()
    state.seen("127.0.0.1", "codex/1.0", "Codex")
    current[0] += 120
    assert state.snapshot()["clients"] == []


def test_panel_shows_plain_json_without_config_controls():
    app = QApplication.instance() or QApplication([])
    panel = McpServerInterface()
    try:
        url = panel._endpoint_url()
        assert url.endswith("/mcp/")
        assert url in panel._endpoint.text()
        assert json.loads(panel._config.text()) == {"mcpServers": {"wordagent": {"url": url}}}
        assert panel._config.textInteractionFlags() & Qt.TextSelectableByMouse
        assert not hasattr(panel, "_copy_config_button")
    finally:
        panel.close()
        panel.deleteLater()
        app.processEvents()
