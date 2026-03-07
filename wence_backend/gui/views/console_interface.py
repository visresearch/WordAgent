"""终端界面 - 使用 qfluentwidgets 组件 + QWidget 基类

核心思路：
  OutputBuffer 在 QApplication 创建之前就替换 sys.stdout/stderr，
  这样 uvicorn / logging 等拿到的 stream 引用也是我们的 wrapper。
  ConsoleInterface 通过 QTimer 以 100 ms 间隔轮询缓冲区并显示。
"""

import sys
import threading
from collections import deque

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QTextCursor, QColor
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPlainTextEdit,
)
from qfluentwidgets import (
    SubtitleLabel,
    CaptionLabel,
    PushButton,
    FluentIcon,
    CardWidget,
)


# ────────────────────────────────────────────────────────────
# 线程安全输出缓冲区（不依赖 Qt，可在任何时机安装）
# ────────────────────────────────────────────────────────────


class OutputBuffer:
    """全局单例，替换 sys.stdout / sys.stderr 并缓冲所有输出"""

    _instance: "OutputBuffer | None" = None

    class _Stream:
        """伪装成文件对象的 wrapper"""

        def __init__(self, buf: "OutputBuffer", name: str, original):
            self._buf = buf
            self._name = name
            self.original = original
            self.encoding = getattr(original, "encoding", "utf-8")

        def write(self, text: str):
            if text:
                if self.original:
                    self.original.write(text)
                with self._buf._lock:
                    self._buf._deque.append((text, self._name))

        def flush(self):
            if self.original:
                self.original.flush()

        def fileno(self):
            if self.original:
                return self.original.fileno()
            raise OSError("no underlying fileno")

        def isatty(self):
            return False

    def __init__(self):
        self._deque: deque = deque(maxlen=50000)
        self._lock = threading.Lock()
        self.stdout_stream = self._Stream(self, "stdout", sys.stdout)
        self.stderr_stream = self._Stream(self, "stderr", sys.stderr)

    @classmethod
    def install(cls) -> "OutputBuffer":
        """替换 sys.stdout / sys.stderr，返回单例"""
        if cls._instance is None:
            cls._instance = cls()
            sys.stdout = cls._instance.stdout_stream  # type: ignore[assignment]
            sys.stderr = cls._instance.stderr_stream  # type: ignore[assignment]
        return cls._instance

    @classmethod
    def get(cls) -> "OutputBuffer | None":
        return cls._instance

    def drain(self) -> list[tuple[str, str]]:
        """取出并清空缓冲区，返回 [(text, stream_name), ...]"""
        with self._lock:
            items = list(self._deque)
            self._deque.clear()
            return items


# ────────────────────────────────────────────────────────────
# 终端界面
# ────────────────────────────────────────────────────────────


class ConsoleInterface(QWidget):
    """终端输出界面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("consoleInterface")
        self._maxLines = 5000

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(12)

        # --- 标题栏 ---
        header = QHBoxLayout()
        header.setSpacing(10)

        title = SubtitleLabel("终端", self)
        header.addWidget(title)
        header.addStretch(1)

        self._clearBtn = PushButton(FluentIcon.DELETE, "清空", self)
        self._clearBtn.setToolTip("清空日志")
        self._clearBtn.clicked.connect(self._clearLog)
        header.addWidget(self._clearBtn)

        self._scrollBtn = PushButton(FluentIcon.DOWN, "底部", self)
        self._scrollBtn.setToolTip("滚动到底部")
        self._scrollBtn.clicked.connect(self._scrollToBottom)
        header.addWidget(self._scrollBtn)

        layout.addLayout(header)

        hint = CaptionLabel("显示应用运行过程中的所有日志输出", self)
        hint.setTextColor(QColor("#888888"), QColor("#aaaaaa"))
        layout.addWidget(hint)

        # --- 日志区（包裹在 CardWidget 中） ---
        card = CardWidget(self)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(2, 2, 2, 2)

        self._textEdit = QPlainTextEdit(card)
        self._textEdit.setReadOnly(True)
        self._textEdit.setFont(QFont("Consolas, Menlo, monospace", 11))
        self._textEdit.setStyleSheet(
            """
            QPlainTextEdit {
                background: #1e1e1e;
                color: #d4d4d4;
                border: none;
                border-radius: 6px;
                padding: 8px;
                selection-background-color: #264f78;
            }
            """
        )
        self._textEdit.setLineWrapMode(QPlainTextEdit.NoWrap)
        card_layout.addWidget(self._textEdit)
        layout.addWidget(card, 1)

        # --- 从全局 OutputBuffer 轮询 ---
        self._buf = OutputBuffer.get()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._pollBuffer)
        self._timer.start(100)

        self._pollBuffer()

    def _pollBuffer(self):
        if self._buf is None:
            return
        items = self._buf.drain()
        if not items:
            return
        for text, stream_name in items:
            self._appendText(text, stream_name)

    def _appendText(self, text: str, stream_name: str):
        cursor = self._textEdit.textCursor()
        cursor.movePosition(QTextCursor.End)

        if stream_name == "stderr":
            fmt = cursor.charFormat()
            fmt.setForeground(QColor("#f48771"))
            cursor.setCharFormat(fmt)
            cursor.insertText(text)
            fmt.setForeground(QColor("#d4d4d4"))
            cursor.setCharFormat(fmt)
        else:
            cursor.insertText(text)

        if self._textEdit.blockCount() > self._maxLines:
            cursor.movePosition(QTextCursor.Start)
            cursor.movePosition(
                QTextCursor.Down,
                QTextCursor.KeepAnchor,
                self._textEdit.blockCount() - self._maxLines,
            )
            cursor.removeSelectedText()

        self._textEdit.setTextCursor(cursor)
        self._textEdit.ensureCursorVisible()

    def _clearLog(self):
        self._textEdit.clear()

    def _scrollToBottom(self):
        cursor = self._textEdit.textCursor()
        cursor.movePosition(QTextCursor.End)
        self._textEdit.setTextCursor(cursor)
        self._textEdit.ensureCursorVisible()

    def destroy(self, *args, **kwargs):
        self._timer.stop()
        if self._buf:
            sys.stdout = self._buf.stdout_stream.original
            sys.stderr = self._buf.stderr_stream.original
        super().destroy(*args, **kwargs)
