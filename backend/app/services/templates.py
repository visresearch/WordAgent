"""Persist reusable document templates and create editable copies."""

import json
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID, uuid4
from zipfile import BadZipFile, ZipFile

from app.core.config import get_wence_project_dir

MAX_TEMPLATE_BYTES = 50 * 1024 * 1024
MAX_INSTRUCTIONS_LENGTH = 50_000
_SUPPORTED_SUFFIXES = {".doc", ".docx"}
_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff", ".svg", ".emf", ".wmf"}


def get_template_root() -> Path:
    root = get_wence_project_dir().resolve() / "template"
    root.mkdir(exist_ok=True)
    return root


def _get_folder(template_id: UUID) -> Path:
    folder = get_template_root() / str(template_id)
    if not folder.is_dir() or folder.is_symlink():
        raise FileNotFoundError("Template not found")
    return folder


def _get_file(folder: Path, name: str) -> Path:
    path = folder / name
    if not path.is_file() or path.is_symlink():
        raise FileNotFoundError("Template file not found")
    return path


def _read_metadata(folder: Path) -> dict:
    return json.loads(_get_file(folder, "metadata.json").read_text(encoding="utf-8"))


def list_templates() -> list[dict]:
    entries = []
    for folder in get_template_root().iterdir():
        try:
            template_id = UUID(folder.name)
            if str(template_id) == folder.name:
                entries.append(_read_metadata(_get_folder(template_id)))
        except (FileNotFoundError, ValueError):
            continue
    return sorted(entries, key=lambda entry: entry.get("createdAt", ""), reverse=True)


def get_template(template_id: UUID) -> dict:
    folder = _get_folder(template_id)
    instructions = _get_file(folder, "instructions.md").read_text(encoding="utf-8")
    return {**_read_metadata(folder), "instructions": instructions}


def get_template_original(template_id: UUID) -> Path:
    folder = _get_folder(template_id)
    for suffix in (".docx", ".doc"):
        path = folder / f"original{suffix}"
        if path.is_file() and not path.is_symlink():
            return path
    raise FileNotFoundError("Template original not found")


def get_template_cover(template_id: UUID) -> Path:
    folder = _get_folder(template_id)
    for suffix in (".png", ".jpg"):
        path = folder / f"cover{suffix}"
        if path.is_file() and not path.is_symlink():
            return path
    raise FileNotFoundError("Template cover not found")


def _extract_thumbnail(source: Path, folder: Path) -> bool:
    if source.suffix == ".doc":
        with source.open("rb") as stream:
            if stream.read(8) != bytes.fromhex("d0cf11e0a1b11ae1"):
                raise ValueError("The source is not a valid DOC file")
        return False
    try:
        with ZipFile(source) as package:
            entries = set(package.namelist())
            if not {"[Content_Types].xml", "word/document.xml"}.issubset(entries):
                raise ValueError("The source is not a valid DOCX file")
            for name in ("docProps/thumbnail.png", "docProps/thumbnail.jpeg", "docProps/thumbnail.jpg"):
                if name not in entries or package.getinfo(name).file_size > 2 * 1024 * 1024:
                    continue
                preview = package.read(name)
                if preview.startswith(b"\x89PNG\r\n\x1a\n"):
                    (folder / "cover.png").write_bytes(preview)
                    return True
                if preview.startswith(b"\xff\xd8\xff"):
                    (folder / "cover.jpg").write_bytes(preview)
                    return True
    except BadZipFile as exc:
        raise ValueError("The source is not a valid DOCX file") from exc
    return False


def _cover_lines(document: dict) -> list[dict]:
    paragraphs = document["paragraphs"]
    styles = document.get("styles", {})
    first_page = next(
        (block["pageStart"] for block in paragraphs
         if isinstance(block, dict) and isinstance(block.get("pageStart"), int) and block["pageStart"] > 0),
        None,
    )
    lines = []
    for block in paragraphs:
        if not isinstance(block, dict):
            continue
        page = block.get("pageStart")
        if first_page is not None and isinstance(page, int) and page > first_page:
            break
        runs = block.get("runs")
        if not isinstance(runs, list):
            continue
        text = "".join(
            str(run.get("text") or "").replace("\r", " ").replace("\n", " ")
            for run in runs
            if isinstance(run, dict)
        ).strip()
        if not text:
            continue
        paragraph_style = styles.get(str(block.get("pStyle")), [])
        style_name = str(paragraph_style[7]) if isinstance(paragraph_style, list) and len(paragraph_style) > 7 else ""
        lines.append({
            "text": text[:120],
            "heading": not lines or bool(re.search(r"title|heading|标题|题目", style_name, re.I)),
            "centered": isinstance(paragraph_style, list)
            and bool(paragraph_style) and paragraph_style[0] in (1, "center"),
        })
        if len(lines) >= 8:
            break
    return lines


def _archive_images(document: dict, folder: Path, destination: Path) -> None:
    """Keep converter-exported images alongside the JSON across cache cleanup."""
    project = get_wence_project_dir().resolve()
    cache_dirs = {project / "temp", project / "uploads"}
    archived: dict[Path, str] = {}

    def visit(value):
        if isinstance(value, list):
            for item in value:
                visit(item)
        elif isinstance(value, dict):
            for key, item in value.items():
                if key == "url" and isinstance(item, str) and not item.startswith(("data:", "http:", "https:", "file:")):
                    source = (project / item).resolve()
                    if source.parent in cache_dirs and source.suffix.lower() in _IMAGE_SUFFIXES and source.is_file():
                        if source not in archived:
                            name = f"{len(archived) + 1}{source.suffix.lower()}"
                            assets = folder / "assets"
                            assets.mkdir(exist_ok=True)
                            shutil.copyfile(source, assets / name)
                            archived[source] = (destination / "assets" / name).relative_to(project).as_posix()
                        value[key] = archived[source]
                else:
                    visit(item)

    visit(document)


def save_template(template_id: UUID, name: str, instructions: str, original_name: str, original: bytes, raw_json: bytes) -> dict:
    name = name.strip()
    instructions = instructions.strip()
    if not name or len(name) > 120 or not instructions or len(instructions) > MAX_INSTRUCTIONS_LENGTH:
        raise ValueError("A template requires a name and Markdown instructions")
    original_name = re.split(r"[/\\]", original_name)[-1]
    suffix = Path(original_name).suffix.lower()
    if suffix not in _SUPPORTED_SUFFIXES:
        raise ValueError("Only DOC and DOCX templates are supported")
    if not original or not raw_json or max(len(original), len(raw_json)) > MAX_TEMPLATE_BYTES:
        raise ValueError("Each template file must contain between 1 byte and 50 MB")
    document = json.loads(raw_json)
    if not isinstance(document, dict) or not isinstance(document.get("paragraphs"), list):
        raise ValueError("A full DocxJSON document is required")
    if not isinstance(document.get("styles", {}), dict) or document.get("_lightweight"):
        raise ValueError("A full DocxJSON document is required")

    root = get_template_root()
    destination = root / str(template_id)
    if destination.exists():
        return _read_metadata(_get_folder(template_id))

    # Readers only see a template after all three artifacts have been written.
    with TemporaryDirectory(prefix=".archiving-", dir=root) as temporary:
        folder = Path(temporary) / "template"
        folder.mkdir()
        source = folder / f"original{suffix}"
        source.write_bytes(original)
        has_thumbnail = _extract_thumbnail(source, folder)
        _archive_images(document, folder, destination)
        metadata = {
            "id": str(template_id),
            "name": name,
            "originalName": original_name,
            "format": suffix[1:],
            "createdAt": datetime.now(UTC).isoformat(),
            "hasThumbnail": has_thumbnail,
            "coverLines": _cover_lines(document),
        }
        (folder / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")
        (folder / "document.json").write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
        (folder / "instructions.md").write_text(instructions + "\n", encoding="utf-8")
        try:
            folder.rename(destination)
        except OSError:
            if not destination.is_dir():
                raise
            return _read_metadata(_get_folder(template_id))
    return metadata


def create_template_copy(template_id: UUID) -> Path:
    original = get_template_original(template_id)
    metadata = _read_metadata(original.parent)
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", metadata["name"]).strip(" .")[:75] or "Template"
    folder = get_wence_project_dir() / "documents" / uuid4().hex
    folder.mkdir(parents=True)
    copy = folder / f"{name}{original.suffix}"
    try:
        shutil.copyfile(original, copy)
    except OSError:
        shutil.rmtree(folder)
        raise
    return copy.resolve()
