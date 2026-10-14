"""MS Office 加载项安装界面"""

import os
import ssl
import sys
import threading
import webbrowser
import datetime
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFileDialog
from qfluentwidgets import (
    SubtitleLabel,
    CaptionLabel,
    CardWidget,
    PushButton,
    BodyLabel,
    InfoBar,
    InfoBarPosition,
)
from gui.i18n import t

from app.core.config import get_wence_data_dir
from app.core.logging import get_logger

logger = get_logger("gui.office_install")


class OfficeStaticRequestHandler(SimpleHTTPRequestHandler):
    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".js": "application/javascript",
        ".html": "text/html",
        ".css": "text/css",
        ".xml": "application/xml",
        ".json": "application/json",
        ".png": "image/png",
        ".svg": "image/svg+xml",
    }
    image_extensions = frozenset({".png", ".svg", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".webp", ".ico"})

    def end_headers(self):
        extension = Path(unquote(urlsplit(self.path).path)).suffix.lower()
        # Office substitutes its default icon if image responses set Cache-Control.
        # https://learn.microsoft.com/en-us/javascript/api/manifest/image
        if extension not in self.image_extensions:
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def log_message(self, format, *args):
        message = format % args
        if " 200 " in f" {message} " or " 304 " in f" {message} ":
            logger.debug("Office static server: %s - %s", self.address_string(), message)
        else:
            logger.warning("Office static server: %s - %s", self.address_string(), message)


def _get_runtime_base() -> Path:
    """获取 backend 运行时基础目录（兼容 PyInstaller）。"""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[2]


def _get_workspace_base() -> Path:
    """获取工作区根目录。"""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return _get_runtime_base().parent


def _get_resource_manifest() -> Path | None:
    """获取 gui/resources 下的 manifest.xml。"""
    base = _get_runtime_base()
    if getattr(sys, "frozen", False):
        candidates = [
            base / "resources" / "manifest.xml",
            base / "gui" / "resources" / "manifest.xml",
            base / "manifest.xml",
        ]
    else:
        candidates = [
            base / "gui" / "resources" / "manifest.xml",
            base / "resources" / "manifest.xml",
        ]

    for path in candidates:
        if path.exists():
            return path
    return None


def _get_frontend_dist_dir() -> Path | None:
    """获取 microsoft_word_plugin 的 dist 目录。"""
    base = _get_workspace_base()
    if getattr(sys, "frozen", False):
        candidates = [
            base / "msoffice",
            base / "frontend" / "microsoft_word_plugin" / "dist",
        ]
    else:
        candidates = [base / "frontend" / "microsoft_word_plugin" / "dist"]

    for path in candidates:
        if path.exists():
            return path
    return None


def _get_persistent_cert_dir() -> Path:
    """获取可持久化证书目录。"""
    return get_wence_data_dir() / "certs"


def _generate_localhost_cert(target_dir: Path) -> tuple[Path, Path]:
    """生成自签名 localhost 证书和私钥。"""
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    target_dir.mkdir(parents=True, exist_ok=True)
    cert_file = target_dir / "localhost.crt"
    key_file = target_dir / "localhost-key.pem"

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "WenCe AI"),
            x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
        ]
    )

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.UTC))
        .not_valid_after(datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=365))
        .add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.DNSName("localhost"),
                ]
            ),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )

    key_file.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    cert_file.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    return cert_file, key_file


def _get_cert_paths() -> tuple[Path, Path]:
    """获取 HTTPS 证书路径。优先复用，缺失时自动生成。"""
    persistent_dir = _get_persistent_cert_dir()
    cert_file = persistent_dir / "localhost.crt"
    key_file = persistent_dir / "localhost-key.pem"
    if cert_file.exists() and key_file.exists():
        return cert_file, key_file

    try:
        return _generate_localhost_cert(persistent_dir)
    except Exception as e:
        raise FileNotFoundError(
            f"未找到可用 localhost 证书，且自动生成失败：{e}。请检查 wence_data/certs 目录权限。"
        ) from e


class OfficeInstallInterface(QWidget):
    """MS Office 加载项安装管理界面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("officeInstallInterface")

        self._host = "localhost"
        self._port = 3000
        self._server: ThreadingHTTPServer | None = None
        self._server_thread: threading.Thread | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(12)

        self._title_label = SubtitleLabel(t("office.title"), self)
        layout.addWidget(self._title_label)

        self._subtitle_label = CaptionLabel(t("office.subtitle"), self)
        self._subtitle_label.setTextColor(QColor("#888888"), QColor("#aaaaaa"))
        layout.addWidget(self._subtitle_label)

        card = CardWidget(self)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(12)

        self._usage_label = BodyLabel(t("office.usage"), card)
        self._usage_label.setTextFormat(Qt.RichText)
        self._usage_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self._usage_label.setOpenExternalLinks(True)
        self._usage_label.setWordWrap(True)
        card_layout.addWidget(self._usage_label)

        self._service_status_label = BodyLabel("", card)
        card_layout.addWidget(self._service_status_label)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self._download_btn = PushButton(t("office.buttons.download"), card)
        self._download_btn.clicked.connect(self._on_download_manifest)
        btn_layout.addWidget(self._download_btn)

        self._start_btn = PushButton(t("office.buttons.start"), card)
        self._start_btn.clicked.connect(self._on_start_service)
        btn_layout.addWidget(self._start_btn)

        self._install_cert_btn = PushButton(t("office.buttons.installCert"), card)
        self._install_cert_btn.clicked.connect(self._on_install_cert)
        btn_layout.addWidget(self._install_cert_btn)

        self._open_browser_btn = PushButton(t("office.buttons.openBrowser"), card)
        self._open_browser_btn.clicked.connect(self._on_open_browser)
        btn_layout.addWidget(self._open_browser_btn)

        self._stop_btn = PushButton(t("office.buttons.stop"), card)
        self._stop_btn.clicked.connect(self._on_stop_service)
        btn_layout.addWidget(self._stop_btn)

        btn_layout.addStretch()
        card_layout.addLayout(btn_layout)

        layout.addWidget(card)
        layout.addStretch()

        self._update_service_status()
        from gui.i18n import subscribe_locale_changed

        subscribe_locale_changed(self._retranslate)
        QTimer.singleShot(0, self._on_start_service)

    def _update_service_status(self):
        running = self._server is not None and self._server_thread is not None
        if running:
            self._service_status_label.setText(t("office.status.running", host=self._host, port=self._port))
            self._service_status_label.setStyleSheet("color: #16a34a;")
            self._start_btn.setEnabled(False)
            self._open_browser_btn.setEnabled(True)
            self._stop_btn.setEnabled(True)
        else:
            self._service_status_label.setText(t("office.status.stopped"))
            self._service_status_label.setStyleSheet("color: #d97706;")
            self._start_btn.setEnabled(True)
            self._open_browser_btn.setEnabled(False)
            self._stop_btn.setEnabled(False)

    def _on_download_manifest(self):
        src_manifest = _get_resource_manifest()
        if not src_manifest:
            InfoBar.error(
                title=t("office.infobar.downloadFailed.title"),
                content=t("office.infobar.downloadFailed.contentMissing"),
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3500,
            )
            return

        default_path = str(Path.home() / "Desktop" / "manifest.xml")
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            t("office.dialog.saveManifest"),
            default_path,
            t("office.dialog.xmlFilter"),
        )
        if not save_path:
            return

        try:
            Path(save_path).write_bytes(src_manifest.read_bytes())
            InfoBar.success(
                title=t("office.infobar.downloadSuccess.title"),
                content=t("office.infobar.downloadSuccess.content", path=save_path),
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3500,
            )
        except Exception as e:
            InfoBar.error(
                title="下载失败",
                content=str(e),
                parent=self,
                position=InfoBarPosition.TOP,
                duration=5000,
            )

    def _on_open_browser(self):
        """用系统浏览器打开服务地址，让用户接受自签名证书。"""
        url = f"https://{self._host}:{self._port}/taskpane.html"
        try:
            webbrowser.open(url)
            InfoBar.info(
                title=t("office.infobar.openBrowser.title"),
                content="",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=4000,
            )
        except Exception as e:
            InfoBar.error(
                title=t("office.infobar.openBrowserFailed.title"),
                content=str(e),
                parent=self,
                position=InfoBarPosition.TOP,
                duration=4000,
            )

    def _on_install_cert(self):
        """打开 .crt 文件，让用户在系统证书界面手动安装。"""
        try:
            cert_file, _ = _get_cert_paths()

            if sys.platform.startswith("win"):
                os.startfile(str(cert_file))
            else:
                webbrowser.open(cert_file.as_uri())

            InfoBar.info(
                title=t("office.infobar.certOpened.title"),
                content=t("office.infobar.certOpened.content"),
                parent=self,
                position=InfoBarPosition.TOP,
                duration=5000,
            )
        except Exception as e:
            InfoBar.error(
                title=t("office.infobar.certFailed.title"),
                content=str(e),
                parent=self,
                position=InfoBarPosition.TOP,
                duration=5000,
            )

    def _on_start_service(self):
        if self._server is not None:
            InfoBar.warning(
                title=t("office.infobar.serviceRunning.title"),
                content=t("office.infobar.serviceRunning.content"),
                parent=self,
                position=InfoBarPosition.TOP,
                duration=2500,
            )
            return

        dist_dir = _get_frontend_dist_dir()
        if not dist_dir:
            InfoBar.error(
                title=t("office.infobar.startFailed.title"),
                content=t("office.infobar.startFailed.contentMissingDist"),
                parent=self,
                position=InfoBarPosition.TOP,
                duration=4000,
            )
            return

        try:
            cert_file, key_file = _get_cert_paths()

            handler = partial(OfficeStaticRequestHandler, directory=str(dist_dir))

            server = ThreadingHTTPServer((self._host, self._port), handler)
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ctx.load_cert_chain(certfile=str(cert_file), keyfile=str(key_file))
            server.socket = ctx.wrap_socket(server.socket, server_side=True)

            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()

            self._server = server
            self._server_thread = thread
            self._update_service_status()
            InfoBar.success(
                title=t("office.infobar.startSuccess.title"),
                content=t("office.infobar.startSuccess.content", host=self._host, port=self._port),
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3500,
            )
        except Exception as e:
            if self._server:
                try:
                    self._server.server_close()
                except Exception:
                    pass
            self._server = None
            self._server_thread = None
            self._update_service_status()
            InfoBar.error(
                title="启动失败",
                content=str(e),
                parent=self,
                position=InfoBarPosition.TOP,
                duration=5000,
            )

    def _on_stop_service(self):
        if self._server is None:
            InfoBar.warning(
                title=t("office.infobar.notRunning.title"),
                content=t("office.infobar.notRunning.content"),
                parent=self,
                position=InfoBarPosition.TOP,
                duration=2500,
            )
            return

        try:
            self._server.shutdown()
            self._server.server_close()
            if self._server_thread is not None:
                self._server_thread.join(timeout=2)

            self._server = None
            self._server_thread = None
            self._update_service_status()
            InfoBar.success(
                title=t("office.infobar.stopped.title"),
                content=t("office.infobar.stopped.content"),
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000,
            )
        except Exception as e:
            InfoBar.error(
                title=t("office.infobar.stopFailed.title"),
                content=str(e),
                parent=self,
                position=InfoBarPosition.TOP,
                duration=5000,
            )

    def _retranslate(self, _locale: str = ""):
        """Update all translatable labels on this page."""
        self._title_label.setText(t("office.title"))
        self._subtitle_label.setText(t("office.subtitle"))
        self._usage_label.setText(t("office.usage"))
        self._download_btn.setText(t("office.buttons.download"))
        self._start_btn.setText(t("office.buttons.start"))
        self._install_cert_btn.setText(t("office.buttons.installCert"))
        self._open_browser_btn.setText(t("office.buttons.openBrowser"))
        self._stop_btn.setText(t("office.buttons.stop"))
        self._update_service_status()

    def closeEvent(self, event):
        """界面关闭时自动停止后台服务。"""
        if self._server is not None:
            try:
                self._server.shutdown()
                self._server.server_close()
                if self._server_thread is not None:
                    self._server_thread.join(timeout=2)
            except Exception:
                pass
            finally:
                self._server = None
                self._server_thread = None
        super().closeEvent(event)
