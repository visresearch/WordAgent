"""Render native Word/WPS page layouts to PNG and prepare images for vision models."""

from __future__ import annotations

import base64
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Literal
from uuid import UUID

from PySide6.QtCore import QBuffer, QIODevice, QSize, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtPdf import QPdfDocument

from app.core.config import get_temp_dir

ViewMode = Literal["single", "combine"]
RENDER_DPI = 120
MAX_PDF_BYTES = 50 * 1024 * 1024
# A 32-bit canvas with this area can already occupy 160 MB of RAM.
MAX_RENDER_PIXELS = 40_000_000
# Keep long images within common model input limits without resizing the saved PNG.
_VISION_MAX_EDGE = 8_000
_VISION_PNG_BYTES = 768 * 1024


def view_images(request_id: UUID, page_start: int, page_end: int, mode: ViewMode) -> list[tuple[str, Path]]:
    directory = get_temp_dir().resolve() / "view_document" / str(request_id)
    if mode == "combine":
        return [(f"Pages {page_start}–{page_end}", directory / f"pages-{page_start:04d}-{page_end:04d}.png")]
    return [(f"Page {page}", directory / f"page-{page:04d}.png") for page in range(page_start, page_end + 1)]


def _render_page(document: QPdfDocument, page: int, size: QSize) -> QImage:
    image = document.render(page, size)
    if image.isNull():
        raise ValueError(f"Unable to render document page {page + 1}.")
    return image


def _write_png(image: QImage, target: Path) -> None:
    dots_per_meter = round(RENDER_DPI / 0.0254)
    image.setDotsPerMeterX(dots_per_meter)
    image.setDotsPerMeterY(dots_per_meter)
    if not image.save(str(target), "PNG"):
        raise OSError(f"Unable to save rendered page image {target.name}.")


def _white_canvas(width: int, height: int) -> QImage:
    image = QImage(width, height, QImage.Format.Format_RGB32)
    if image.isNull():
        raise ValueError("Unable to allocate the page image. Request a smaller page range.")
    image.fill(Qt.GlobalColor.white)
    return image


def render_document_view(
    pdf: bytes, request_id: UUID, page_start: int, page_end: int, mode: ViewMode
) -> None:
    """Use the editor's exported PDF layout and retain the source paper proportions."""
    if page_start < 1 or page_end < page_start:
        raise ValueError("Require 1 <= page_start <= page_end.")
    if mode not in ("single", "combine"):
        raise ValueError("mode must be 'single' or 'combine'.")
    if not pdf or len(pdf) > MAX_PDF_BYTES:
        raise ValueError("The editor's temporary PDF must contain between 1 byte and 50 MB.")

    buffer = QBuffer()
    buffer.setData(pdf)
    buffer.open(QIODevice.OpenModeFlag.ReadOnly)
    document = QPdfDocument(None)
    try:
        document.load(buffer)
        if document.status() != QPdfDocument.Status.Ready:
            raise ValueError("The editor supplied a PDF that could not be opened.")
        if page_end > document.pageCount():
            raise ValueError(f"The document has {document.pageCount()} pages. Requested page {page_end} is out of range.")

        sizes = []
        for page in range(page_start - 1, page_end):
            size = document.pagePointSize(page)
            sizes.append(QSize(
                max(1, round(size.width() * RENDER_DPI / 72)),
                max(1, round(size.height() * RENDER_DPI / 72)),
            ))
        width = max(size.width() for size in sizes)
        height = sum(size.height() for size in sizes)
        pixels = width * height if mode == "combine" else sum(size.width() * size.height() for size in sizes)
        if pixels > MAX_RENDER_PIXELS:
            raise ValueError(f"The range exceeds the render size limit at {RENDER_DPI} DPI. Request fewer pages per call.")

        images = view_images(request_id, page_start, page_end, mode)
        directory = images[0][1].parent
        directory.parent.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(prefix=".render-", dir=directory.parent) as staging:
            output = Path(staging) / "images"
            output.mkdir()
            if mode == "combine":
                canvas = _white_canvas(width, height)
                y = 0
                with QPainter(canvas) as painter:
                    for page, size in enumerate(sizes, start=page_start - 1):
                        painter.drawImage((width - size.width()) // 2, y, _render_page(document, page, size))
                        y += size.height()
                _write_png(canvas, output / images[0][1].name)
            else:
                for page, (size, (_, target)) in enumerate(zip(sizes, images, strict=True), start=page_start - 1):
                    canvas = _white_canvas(size.width(), size.height())
                    with QPainter(canvas) as painter:
                        painter.drawImage(0, 0, _render_page(document, page, size))
                    _write_png(canvas, output / target.name)
            output.rename(directory)
    finally:
        document.close()


def document_view_image_block(path: Path) -> dict:
    """Encode only an image generated in the preview cache for the next model call."""
    root = get_temp_dir().resolve() / "view_document"
    resolved = path.resolve(strict=True)
    if resolved.parent.parent != root or resolved != path or resolved.suffix != ".png":
        raise ValueError("Invalid rendered document image path.")
    image = QImage(str(resolved))
    if image.isNull():
        raise ValueError("Unable to open the rendered document image.")

    if max(image.width(), image.height()) <= _VISION_MAX_EDGE and resolved.stat().st_size <= _VISION_PNG_BYTES:
        payload = resolved.read_bytes()
        mime = "image/png"
    else:
        if max(image.width(), image.height()) > _VISION_MAX_EDGE:
            image = image.scaled(
                _VISION_MAX_EDGE, _VISION_MAX_EDGE,
                Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation,
            )
        encoded = QBuffer()
        encoded.open(QIODevice.OpenModeFlag.WriteOnly)
        if not image.save(encoded, "JPEG", 82):
            raise ValueError("Unable to encode the rendered page for vision.")
        payload = bytes(encoded.data())
        mime = "image/jpeg"
    return {"type": "image", "mime_type": mime, "base64": base64.b64encode(payload).decode("ascii")}
