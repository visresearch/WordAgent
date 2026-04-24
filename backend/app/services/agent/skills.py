"""Skill discovery and loading helpers for the main agent."""

from __future__ import annotations

import json
import shutil
import tempfile
import zipfile
from pathlib import Path

from app.core.config import get_user_settings_file, get_wence_data_dir


def _skills_root() -> Path:
    """Return skills root directory under wence_data."""
    root = get_wence_data_dir() / "skills"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _load_skill_enable_map() -> dict[str, bool]:
    """Read persisted skill enable states from user settings file."""
    settings_file = get_user_settings_file()
    if not settings_file.exists():
        return {}

    try:
        data = json.loads(settings_file.read_text(encoding="utf-8"))
    except Exception:
        return {}

    raw_map = data.get("skillStates")
    if not isinstance(raw_map, dict):
        return {}

    result: dict[str, bool] = {}
    for key, value in raw_map.items():
        if isinstance(key, str):
            result[key] = bool(value)
    return result


def _write_skill_enable_map(mapping: dict[str, bool]) -> None:
    """Persist skill enable states to user settings file."""
    settings_file = get_user_settings_file()
    settings_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        data = json.loads(settings_file.read_text(encoding="utf-8")) if settings_file.exists() else {}
    except Exception:
        data = {}

    data["skillStates"] = {str(k): bool(v) for k, v in mapping.items()}
    settings_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _validate_folder_key(folder: str) -> str:
    """Validate folder key from API input."""
    folder_key = (folder or "").strip()
    if not folder_key:
        raise ValueError("folder cannot be empty")
    if folder_key in {".", ".."}:
        raise ValueError("invalid folder")
    if Path(folder_key).name != folder_key:
        raise ValueError("invalid folder")
    if any(ch in folder_key for ch in '<>:"/\\|?*'):
        raise ValueError("invalid folder")
    return folder_key


def set_skill_enabled(folder: str, enabled: bool) -> None:
    """Set enable state for a skill folder."""
    folder_key = _validate_folder_key(folder)

    mapping = _load_skill_enable_map()
    mapping[folder_key] = bool(enabled)
    _write_skill_enable_map(mapping)


def remove_skill_state(folder: str) -> None:
    """Remove persisted state for deleted skill folder."""
    try:
        folder_key = _validate_folder_key(folder)
    except ValueError:
        return

    mapping = _load_skill_enable_map()
    if folder_key in mapping:
        del mapping[folder_key]
        _write_skill_enable_map(mapping)


def _find_skill_file(skill_dir: Path) -> Path | None:
    """Find SKILL.md in a skill directory (case-insensitive)."""
    try:
        for child in skill_dir.iterdir():
            if child.is_file() and child.name.lower() == "skill.md":
                return child
    except Exception:
        return None
    return None


def _extract_frontmatter(md_text: str) -> tuple[dict[str, str], str]:
    """Extract a simple YAML-like frontmatter and markdown body."""
    text = md_text.lstrip("\ufeff")
    if not text.startswith("---"):
        return {}, text

    parts = text.split("\n---", 1)
    if len(parts) != 2:
        return {}, text

    frontmatter_raw = parts[0][3:].strip("\n\r ")
    body = parts[1].lstrip("\n\r")
    data: dict[str, str] = {}
    for line in frontmatter_raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and value:
            data[key] = value
    return data, body


def discover_skills(include_disabled: bool = True) -> list[dict[str, str | bool]]:
    """Discover skills by scanning directories that contain SKILL.md."""
    root = _skills_root()
    if not root.exists() or not root.is_dir():
        return []

    enabled_map = _load_skill_enable_map()
    result: list[dict[str, str | bool]] = []
    for child in sorted(root.iterdir(), key=lambda p: p.name.lower()):
        if not child.is_dir():
            continue

        skill_file = _find_skill_file(child)
        if not skill_file:
            continue

        try:
            raw = skill_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            raw = ""

        frontmatter, _ = _extract_frontmatter(raw)
        display_name = frontmatter.get("name") or child.name
        description = frontmatter.get("description") or ""
        enabled = enabled_map.get(child.name, True)

        if not include_disabled and not enabled:
            continue

        result.append(
            {
                "name": display_name,
                "folder": child.name,
                "description": description,
                "entry": str(skill_file),
                "enabled": enabled,
            }
        )

    return sorted(result, key=lambda x: x["name"].lower())


def _match_skill(skill_name: str, include_disabled: bool = True) -> dict[str, str | bool] | None:
    """Find a discovered skill by name or folder, case-insensitive."""
    target = (skill_name or "").strip().lower()
    if not target:
        return None

    skills = discover_skills(include_disabled=include_disabled)
    for item in skills:
        name = str(item.get("name", "")).strip().lower()
        folder = str(item.get("folder", "")).strip().lower()
        if name == target or folder == target:
            return item
    return None


def load_skill_context(
    skill_name: str,
    max_total_chars: int = 12000,
    max_file_chars: int = 3000,
    allow_disabled: bool = False,
) -> str:
    """Load SKILL.md and companion markdown files for a discovered skill."""
    matched = _match_skill(skill_name, include_disabled=True)
    if not matched:
        available = ", ".join(str(s["name"]) for s in discover_skills(include_disabled=True)) or "(none)"
        return f"Skill not found: {skill_name}. Available skills: {available}"

    if not allow_disabled and not bool(matched.get("enabled", True)):
        return f"Skill is disabled: {matched['name']}. Enable it in settings before use."

    skill_dir = Path(str(matched["entry"])).parent
    skill_file = Path(str(matched["entry"]))

    chunks: list[str] = []
    total_chars = 0

    def _append_chunk(title: str, content: str):
        nonlocal total_chars
        if not content:
            return
        if total_chars >= max_total_chars:
            return
        content = content[:max_file_chars]
        payload = f"\n## {title}\n{content.strip()}\n"
        remain = max_total_chars - total_chars
        payload = payload[:remain]
        chunks.append(payload)
        total_chars += len(payload)

    try:
        skill_text = skill_file.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        return f"Failed to read skill entry: {skill_file}. Error: {e}"

    _, skill_body = _extract_frontmatter(skill_text)
    _append_chunk("SKILL.md", skill_body or skill_text)

    md_files: list[Path] = []
    try:
        for p in skill_dir.rglob("*.md"):
            if p.name.lower() == "skill.md":
                continue
            md_files.append(p)
    except Exception:
        md_files = []

    for md in sorted(md_files, key=lambda p: str(p.relative_to(skill_dir)).lower()):
        if total_chars >= max_total_chars:
            break
        try:
            text = md.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        rel = md.relative_to(skill_dir).as_posix()
        _append_chunk(rel, text)

    header = (
        f"Skill: {str(matched['name'])}\n"
        f"Folder: {str(matched['folder'])}\n"
        f"Description: {str(matched['description']) or '(none)'}\n"
        "Use this as writing guidance and keep output consistent with the skill rules.\n"
    )
    return header + "\n".join(chunks)


def build_skills_prompt() -> str:
    """Build a compact prompt block that tells agent what skills are available."""
    skills = discover_skills(include_disabled=False)
    if not skills:
        return ""

    lines = [
        "Discovered local skills (auto-scanned from wence_data/skills with SKILL.md):",
    ]
    for s in skills:
        desc = s["description"].strip() or "(no description)"
        if len(desc) > 160:
            desc = desc[:160] + "..."
        lines.append(f"- {s['name']} (folder: {s['folder']}): {desc}")

    lines.extend(
        [
            "When user intent matches a skill, call list_skills first if needed, then call load_skill_context(skill_name).",
            "After loading context, follow skill constraints while using document tools.",
        ]
    )
    return "\n".join(lines)


def _safe_extract_zip(archive_path: Path, target_dir: Path) -> None:
    """Safely extract zip file into target_dir to prevent zip-slip."""
    with zipfile.ZipFile(archive_path, "r") as zf:
        for member in zf.infolist():
            member_name = member.filename
            if not member_name or member_name.endswith("/"):
                continue

            target_path = (target_dir / member_name).resolve()
            if not str(target_path).startswith(str(target_dir.resolve())):
                raise ValueError("Unsafe zip content detected")

        zf.extractall(target_dir)


def install_skill_zip(zip_path: Path, original_filename: str | None = None) -> dict[str, str]:
    """Install skill package from zip file into wence_data/skills."""
    if not zip_path.exists():
        raise FileNotFoundError(f"Zip file not found: {zip_path}")

    with tempfile.TemporaryDirectory(prefix="wence_skill_") as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        _safe_extract_zip(zip_path, temp_dir)

        skill_md_candidates = [p for p in temp_dir.rglob("*") if p.is_file() and p.name.lower() == "skill.md"]
        if not skill_md_candidates:
            raise ValueError("压缩包中未找到 SKILL.md，请上传包含 SKILL.md 的 skill 压缩包")
        if len(skill_md_candidates) > 1:
            raise ValueError("压缩包中包含多个 SKILL.md，请一次只上传一个 skill")

        skill_root = skill_md_candidates[0].parent
        source_folder_name = skill_root.name.strip() or "skill"

        # 如果 SKILL.md 在压缩包根目录，则回退使用 zip 文件名。
        if skill_root == temp_dir:
            source_name = (original_filename or zip_path.name).rsplit(".", 1)[0].strip()
            source_folder_name = source_name or "skill"

        safe_folder_name = "".join(ch for ch in source_folder_name if ch not in '<>:"/\\|?*').strip() or "skill"
        skills_root = _skills_root()
        dest_dir = skills_root / safe_folder_name

        if dest_dir.exists():
            shutil.rmtree(dest_dir)

        shutil.copytree(skill_root, dest_dir)

    # 默认新安装 skill 为启用状态。
    set_skill_enabled(safe_folder_name, True)

    installed = _match_skill(safe_folder_name, include_disabled=True)
    return {
        "name": str(installed.get("name") if installed else safe_folder_name),
        "folder": safe_folder_name,
        "description": str(installed.get("description") if installed else ""),
    }


def delete_skill(folder: str) -> None:
    """Delete a skill folder and clean related enable-state."""
    folder_key = _validate_folder_key(folder)

    target_dir = _skills_root() / folder_key
    if not target_dir.exists() or not target_dir.is_dir():
        raise FileNotFoundError(f"Skill folder not found: {folder_key}")

    shutil.rmtree(target_dir)
    remove_skill_state(folder_key)
