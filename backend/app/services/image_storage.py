"""Store document images locally; model context contains file references only."""

import base64
import hashlib
import re
from pathlib import Path

from app.core.config import get_temp_dir

MAX_IMAGE_BYTES = 50 * 1024 * 1024
_IMAGE_EXTENSIONS = {
    "image/png": ".png", "image/jpeg": ".jpg", "image/jpg": ".jpg",
    "image/gif": ".gif", "image/webp": ".webp", "image/bmp": ".bmp",
    "image/svg+xml": ".svg", "image/tiff": ".tiff",
}
_DATA_IMAGE = re.compile(r"data:(image/[a-zA-Z0-9.+-]+);base64,([A-Za-z0-9+/=]+)", re.IGNORECASE)


def save_image_bytes(content: bytes, media_type: str) -> Path:
    extension = _IMAGE_EXTENSIONS.get(media_type.lower())
    if extension is None:
        raise ValueError("Unsupported image type")
    if not content or len(content) > MAX_IMAGE_BYTES:
        raise ValueError("Image must contain between 1 byte and 50 MB")
    # Repeated reads of the same picture reuse its file instead of filling the cache.
    path = get_temp_dir() / f"image_{hashlib.sha256(content).hexdigest()}{extension}"
    path.write_bytes(content)
    return path.resolve()


def _save_base64_image(encoded: str, media_type: str) -> str:
    if len(encoded) > (MAX_IMAGE_BYTES + 2) // 3 * 4:
        raise ValueError("Image exceeds 50 MB")
    try:
        content = base64.b64decode(encoded, validate=True)
    except ValueError as exc:
        raise ValueError("Invalid Base64 image") from exc
    return save_image_bytes(content, media_type).as_posix()


def persist_inline_images(value):
    """Replace inline image data recursively, including JSON inside tool messages."""
    if isinstance(value, str):
        converted = _DATA_IMAGE.sub(lambda match: _save_base64_image(match[2], match[1]), value)
        if value.lower().startswith("data:image/") and converted == value:
            raise ValueError("Invalid inline image")
        return converted
    if isinstance(value, list):
        return [persist_inline_images(item) for item in value]
    if not isinstance(value, dict):
        return value
    image_type = value.get("type")
    if isinstance(image_type, str) and image_type in {"image_url", "input_image"}:
        reference = value.get("image_url", "")
        if isinstance(reference, dict):
            reference = reference.get("url", "")
        return {"type": "text", "text": f"Image file: {persist_inline_images(reference)}"}
    if image_type == "image":
        source = value.get("source") if isinstance(value.get("source"), dict) else {}
        encoded = value.get("base64") or value.get("data") or source.get("data")
        media_type = value.get("mime_type") or value.get("mimeType") or source.get("media_type")
        if encoded and media_type:
            return {"type": "text", "text": f"Image file: {_save_base64_image(encoded, media_type)}"}
    return {key: persist_inline_images(item) for key, item in value.items()}
