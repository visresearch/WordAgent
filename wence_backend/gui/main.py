"""
WenCe AI GUI - publish.html 窗口
"""

import sys
import os

os.environ["QT_OPENGL"] = "software"

from pathlib import Path
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineScript, QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView


class SafeWebPage(QWebEnginePage):
    def acceptNavigationRequest(self, url, nav_type, is_main_frame):
        scheme = url.scheme().lower()
        if scheme in ("http", "https", "file", "data", "about", "blob", "qrc"):
            return True
        print(f"[拦截] {url.toString()}")
        return False


def start_gui(base_path=None):
    """启动 GUI 窗口，base_path 用于兼容 PyInstaller 打包路径"""
    qt_app = QApplication(sys.argv)

    view = QWebEngineView()
    page = SafeWebPage(view)
    view.setPage(page)

    settings = page.settings()
    settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
    settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)

    early_script = QWebEngineScript()
    early_script.setName("override_init")
    early_script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
    early_script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
    early_script.setSourceCode("""
        window.InitWpsCloudSvr = function() {
            console.log("[GUI] InitWpsCloudSvr 已拦截，跳过自定义协议启动");
        };
    """)
    page.scripts().insert(early_script)

    # 查找 publish.html
    html_path = Path(__file__).parent / "resources" / "publish.html"
    if base_path:
        packed_path = Path(base_path) / "gui" / "resources" / "publish.html"
        if packed_path.exists():
            html_path = packed_path

    if html_path.exists():
        view.setUrl(QUrl.fromLocalFile(str(html_path.resolve())))
    else:
        view.setHtml("<h2 style='text-align:center;margin-top:40px;color:#666;'>publish.html 未找到</h2>")

    view.resize(900, 600)
    view.setWindowTitle("WPS 加载项配置")
    view.show()

    qt_app.exec()


if __name__ == "__main__":
    start_gui()
