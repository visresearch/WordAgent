"""The language picker updates real navigation widgets and their tooltips."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication, QWidget

from gui import i18n
from gui.views import home_interface, main_window


@pytest.mark.parametrize("compacted", [True, False])
def test_language_picker_updates_navigation(monkeypatch, compacted):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(i18n, "_initialized", True)
    monkeypatch.setattr(i18n, "_current", "en-US")
    monkeypatch.setattr(i18n, "_write_to_user_settings", lambda _: None)
    monkeypatch.setattr(i18n, "_write_to_qsettings", lambda _: None)
    monkeypatch.setattr(home_interface, "_read_local_version", lambda: "v1.0.0")
    monkeypatch.setattr(home_interface.HomeInterface, "_check_latest_release_async", lambda self: None)
    # Keep the real home page and navigation; other pages need no services here.
    for name in ("DashboardInterface", "InstallInterface", "OfficeInstallInterface", "McpServerInterface", "ConsoleInterface"):
        monkeypatch.setattr(main_window, name, QWidget)

    window = main_window.MainWindow()
    labels = {
        "homeInterface": "home",
        "dashboardInterface": "dashboard",
        "installInterface": "wps",
        "officeInstallInterface": "office",
        "mcpServerInterface": "mcp",
        "consoleInterface": "console",
    }
    try:
        items = {key: window._nav.widget(key) for key in labels}
        for item in items.values():
            item.setCompacted(compacted)
        for index in [0, 1, 2, 3, 4, 5, 0]:
            window._homeInterface._lang_picker.setCurrentIndex(index)
            app.processEvents()
            assert i18n.get_locale() == window._homeInterface._lang_items[index][0]
            for key, label in labels.items():
                item = window._nav.widget(key)
                assert item is items[key]
                assert item.text() == i18n.t(f"nav.{label}")
                assert item.toolTip() == i18n.t(f"nav.{label}")
            assert window._stack.currentWidget() is window._homeInterface

        # Translation preserves the navigation item's existing click handler.
        items["consoleInterface"].clicked.emit(True)
        assert window._stack.currentWidget() is window._consoleInterface
    finally:
        i18n.unsubscribe_locale_changed(window._retranslate_nav)
        window.close()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
