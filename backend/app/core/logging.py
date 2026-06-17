"""
Application logging configuration.

This module keeps logging on the Python standard library so FastAPI,
uvicorn, packaged builds, and future GUI log handlers can share one pipeline.
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

DEFAULT_LOG_FORMAT = "[%(asctime)s][%(levelname)s][%(name)s] %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _get_wence_data_dir() -> Path:
    data_dir = os.environ.get("WENCE_DATA_DIR")
    if data_dir:
        return Path(data_dir)

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "wence_data"

    return Path(__file__).resolve().parents[2] / "wence_data"


def _normalize_log_level(level: str | int | None) -> int:
    if isinstance(level, int):
        return level

    raw = (level or os.environ.get("WORDAGENT_LOG_LEVEL") or os.environ.get("LOG_LEVEL") or "INFO").strip().upper()
    return getattr(logging, raw, logging.INFO)


def _get_log_file() -> Path:
    return get_log_dir() / f"{datetime.now():%Y-%m-%d}.log"


def get_log_dir() -> Path:
    """Return the directory where application log files are stored."""

    return _get_wence_data_dir() / "logs"


def configure_logging(
    *,
    level: str | int | None = None,
    log_file: str | Path | None = None,
    enable_file: bool = True,
    force: bool = False,
) -> None:
    """Configure root, application, and uvicorn loggers.

    The function is intentionally idempotent. Use ``force=True`` only when the
    caller needs to rebuild handlers after replacing stdout/stderr.
    """

    root = logging.getLogger()
    if getattr(root, "_wence_logging_configured", False) and not force:
        return

    log_level = _normalize_log_level(level)
    formatter = logging.Formatter(DEFAULT_LOG_FORMAT, datefmt=DEFAULT_DATE_FORMAT)

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

    for handler in list(root.handlers):
        root.removeHandler(handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(log_level)
    stream_handler.setFormatter(formatter)
    root.addHandler(stream_handler)

    if enable_file:
        target = Path(log_file) if log_file else _get_log_file()
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            file_handler = RotatingFileHandler(
                target,
                maxBytes=5 * 1024 * 1024,
                backupCount=5,
                encoding="utf-8",
            )
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            root.addHandler(file_handler)
        except OSError as exc:
            root.warning("日志文件初始化失败: %s", exc)

    root.setLevel(log_level)
    logging.captureWarnings(True)

    # Let uvicorn use the same handlers and formatting. Passing log_config=None
    # to uvicorn.run keeps these settings intact.
    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.propagate = True
        logger.setLevel(log_level)

    for logger_name in ("sqlalchemy", "sqlalchemy.engine", "sqlalchemy.pool"):
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.propagate = True
        logger.setLevel(logging.WARNING)

    logging.getLogger("wence").setLevel(log_level)
    setattr(root, "_wence_logging_configured", True)


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a project logger."""

    if not name:
        return logging.getLogger("wence")
    if name.startswith("wence"):
        return logging.getLogger(name)
    return logging.getLogger(f"wence.{name}")
