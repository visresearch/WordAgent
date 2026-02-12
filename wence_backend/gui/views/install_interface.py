"""
安装界面 - 点击按钮弹出独立 WebEngine 窗口加载 publish.html
（WebEngine 内嵌 MSFluentWindow 会 segfault，使用独立窗口方案）
"""

from pathlib import Path

from PySide6.QtCore import QUrl, Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QApplication
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineScript, QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView

from qfluentwidgets import (
    PrimaryPushButton,
    TitleLabel,
    SubtitleLabel,
    FluentIcon as FIF,
)


class SafeWebPage(QWebEnginePage):
    """拦截自定义协议(ksoWPSCloudSvr://)导航，防止 WebEngine 崩溃"""

    def acceptNavigationRequest(self, url, nav_type, is_main_frame):
        scheme = url.scheme().lower()
        if scheme in ("http", "https", "file", "data", "about", "blob", "qrc"):
            return True
        print(f"[SafeWebPage] 拦截自定义协议导航: {url.toString()}")
        return False


class PublishWindow(QWebEngineView):
    """独立的 publish.html 窗口（与测试代码一致的方案）"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("WPS 加载项配置")
        self.resize(900, 600)

        # 居中显示
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            screen.width() // 2 - self.width() // 2,
            screen.height() // 2 - self.height() // 2,
        )

        page = SafeWebPage(self)
        self.setPage(page)

        # 允许 file:// 页面访问 http://localhost（WPS 服务端 58890）
        settings = page.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)

        # 在页面 JS 执行前覆盖 InitWpsCloudSvr，防止自定义协议崩溃
        early_script = QWebEngineScript()
        early_script.setName("override_init")
        early_script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
        early_script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
        early_script.setSourceCode(
            'window.InitWpsCloudSvr = function() {  console.log("[GUI] InitWpsCloudSvr 已拦截，跳过自定义协议启动");};'
        )
        page.scripts().insert(early_script)

        self.loadFinished.connect(self._onLoadFinished)

        # 加载 publish.html
        html_path = Path(__file__).resolve().parent.parent / "resources" / "publish.html"
        if html_path.exists():
            self.setUrl(QUrl.fromLocalFile(str(html_path)))
        else:
            self.setHtml("<h2 style='text-align:center;margin-top:40px;color:#666;'>publish.html 未找到</h2>")

    def _onLoadFinished(self, ok):
        if ok:
            self.page().runJavaScript(
                'if (document.querySelectorAll(".addonItem:not(.addonItemTitle)").length === 0) {'
                '  serverVersion = "1.0.0";'
                "  LoadPublishAddons();"
                "  LoadLocalAddons();"
                "}"
            )


class InstallInterface(QWidget):
    """安装管理界面 - 点击按钮打开独立的 publish.html 窗口"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("installInterface")
        self._publish_window = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 40, 36, 36)
        layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        layout.setSpacing(16)

        title = TitleLabel("安装管理", self)
        title.setAlignment(Qt.AlignCenter)

        subtitle = SubtitleLabel("管理 WPS Office 加载项的安装与卸载", self)
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #888;")

        btn = PrimaryPushButton(FIF.DOWNLOAD, "打开加载项配置", self)
        btn.setFixedSize(220, 40)
        btn.clicked.connect(self._openPublishWindow)

        layout.addSpacing(60)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(24)
        layout.addWidget(btn, alignment=Qt.AlignCenter)
        layout.addStretch(1)

    def _openPublishWindow(self):
        """打开独立的 publish.html 窗口"""
        if self._publish_window is None or not self._publish_window.isVisible():
            self._publish_window = PublishWindow()
        self._publish_window.show()
        self._publish_window.activateWindow()
