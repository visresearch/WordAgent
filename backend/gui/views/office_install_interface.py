"""MS Office 加载项安装界面"""

import ssl
import sys
import threading
import webbrowser
from datetime import datetime, timedelta
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
from pathlib import Path

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


def _get_runtime_base() -> Path:
    """获取运行时基础目录（兼容 PyInstaller）。"""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[3]


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
        candidates = [base / "gui" / "resources" / "manifest.xml"]

    for path in candidates:
        if path.exists():
            return path
    return None


def _get_frontend_dist_dir() -> Path | None:
    """获取 microsoft_word_plugin 的 dist 目录。"""
    base = _get_runtime_base()
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
    if getattr(sys, "frozen", False):
        # 打包后使用 exe 同级目录，避免写入 _MEIPASS 临时目录。
        return Path(sys.executable).resolve().parent / "wence_data" / "certs"
    return Path(__file__).resolve().parents[3] / "wence_data" / "certs"


def _generate_localhost_cert(target_dir: Path) -> tuple[Path, Path]:
    """生成自签名 localhost 证书和私钥。"""
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    target_dir.mkdir(parents=True, exist_ok=True)
    cert_file = target_dir / "localhost.crt"
    key_file = target_dir / "localhost.key"

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "WenCe AI"),
            x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
        ]
    )
    now = datetime.utcnow()
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=3650))
        .add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.DNSName("localhost"),
                    x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
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
    runtime_base = _get_runtime_base()
    persistent_dir = _get_persistent_cert_dir()
    candidates = [
        Path.home() / ".office-addin-dev-certs",
        persistent_dir,
        runtime_base / "wence_data" / "certs",
        runtime_base / "certs",
    ]

    for cert_dir in candidates:
        cert_file = cert_dir / "localhost.crt"
        key_file = cert_dir / "localhost.key"
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

        title = SubtitleLabel("Microsoft Word 加载项", self)
        layout.addWidget(title)

        subtitle = CaptionLabel("仅支持 Office 网页版：下载 manifest、启动服务并用浏览器打开接受证书", self)
        subtitle.setTextColor(QColor("#888888"), QColor("#aaaaaa"))
        layout.addWidget(subtitle)

        card = CardWidget(self)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(12)

        self._usage_label = BodyLabel(
            "使用方法：\n"
            "1. 点击“启动 HTTPS 服务”，然后点击“用浏览器打开”在浏览器中接受证书（仅首次需要）。\n"
            "2. 打开 https://word.cloud.microsoft/ 并进入 Word 网页版。\n"
            "3. 进入：开始->加载项->更多加载项->我的加载项->管理我的加载项->上传我的加载项\n"
            "4. 上传下载好的 manifest.xml，完成加载。如果加载项界面未显示，请刷新页面。",
            card,
        )
        self._usage_label.setWordWrap(True)
        card_layout.addWidget(self._usage_label)

        self._service_status_label = BodyLabel("", card)
        card_layout.addWidget(self._service_status_label)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self._download_btn = PushButton("下载 manifest.xml", card)
        self._download_btn.clicked.connect(self._on_download_manifest)
        btn_layout.addWidget(self._download_btn)

        self._start_btn = PushButton("启动 HTTPS 服务", card)
        self._start_btn.clicked.connect(self._on_start_service)
        btn_layout.addWidget(self._start_btn)

        self._open_browser_btn = PushButton("用浏览器打开", card)
        self._open_browser_btn.clicked.connect(self._on_open_browser)
        btn_layout.addWidget(self._open_browser_btn)

        self._stop_btn = PushButton("关闭服务", card)
        self._stop_btn.clicked.connect(self._on_stop_service)
        btn_layout.addWidget(self._stop_btn)

        btn_layout.addStretch()
        card_layout.addLayout(btn_layout)

        layout.addWidget(card)
        layout.addStretch()

        self._update_service_status()

    def _update_service_status(self):
        running = self._server is not None and self._server_thread is not None
        if running:
            self._service_status_label.setText(f"服务状态：运行中（https://{self._host}:{self._port}）")
            self._service_status_label.setStyleSheet("color: #16a34a;")
            self._start_btn.setEnabled(False)
            self._open_browser_btn.setEnabled(True)
            self._stop_btn.setEnabled(True)
        else:
            self._service_status_label.setText("服务状态：未启动")
            self._service_status_label.setStyleSheet("color: #d97706;")
            self._start_btn.setEnabled(True)
            self._open_browser_btn.setEnabled(False)
            self._stop_btn.setEnabled(False)

    def _on_download_manifest(self):
        src_manifest = _get_resource_manifest()
        if not src_manifest:
            InfoBar.error(
                title="下载失败",
                content="未找到 gui/resources/manifest.xml",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3500,
            )
            return

        default_path = str(Path.home() / "Desktop" / "manifest.xml")
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存 manifest.xml",
            default_path,
            "XML 文件 (*.xml)",
        )
        if not save_path:
            return

        try:
            Path(save_path).write_bytes(src_manifest.read_bytes())
            InfoBar.success(
                title="下载成功",
                content=f"manifest.xml 已保存到：{save_path}",
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
                title="已在浏览器中打开",
                content="请在浏览器中接受证书后，回到 Word 网页版刷新加载项。",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=4000,
            )
        except Exception as e:
            InfoBar.error(
                title="打开浏览器失败",
                content=str(e),
                parent=self,
                position=InfoBarPosition.TOP,
                duration=4000,
            )

    def _on_start_service(self):
        if self._server is not None:
            InfoBar.warning(
                title="提示",
                content="HTTPS 服务已在运行",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=2500,
            )
            return

        dist_dir = _get_frontend_dist_dir()
        if not dist_dir:
            InfoBar.error(
                title="启动失败",
                content="未找到 microsoft_word_plugin/dist，请先构建前端",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=4000,
            )
            return

        try:
            cert_file, key_file = _get_cert_paths()

            class LocalStaticHandler(SimpleHTTPRequestHandler):
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

                def end_headers(self):
                    self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                    self.send_header("Pragma", "no-cache")
                    self.send_header("Expires", "0")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    super().end_headers()

            handler = partial(LocalStaticHandler, directory=str(dist_dir))

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
                title="启动成功",
                content=f"HTTPS 服务已启动：https://{self._host}:{self._port}",
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
                title="提示",
                content="HTTPS 服务未启动",
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
                title="已关闭",
                content="HTTPS 服务已停止",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000,
            )
        except Exception as e:
            InfoBar.error(
                title="关闭失败",
                content=str(e),
                parent=self,
                position=InfoBarPosition.TOP,
                duration=5000,
            )

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
