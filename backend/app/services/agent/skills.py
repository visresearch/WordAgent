"""Skill discovery and loading helpers for the main agent."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from app.core.config import get_builtin_skills_dir, get_skills_dir, get_user_settings_file


class SkillAlreadyExistsError(ValueError):
    """Raised when an upload conflicts with an installed skill folder."""


def _skills_root() -> Path:
    """Return skills root directory under wence_data/project."""
    return get_skills_dir()


def _builtin_skill_folders() -> set[str]:
    """Return bundled skill folder names normalized for comparisons."""
    source_root = get_builtin_skills_dir()
    if not source_root.exists() or not source_root.is_dir():
        return set()
    return {
        child.name.casefold()
        for child in source_root.iterdir()
        if child.is_dir() and _find_skill_file(child) is not None
    }


def sync_builtin_skills() -> dict[str, list[str]]:
    """Copy missing bundled skills into the shared user skills directory."""
    source_root = get_builtin_skills_dir()
    if not source_root.exists() or not source_root.is_dir():
        raise FileNotFoundError(f"Builtin skills directory not found: {source_root}")

    skills_root = _skills_root()
    existing_folders = {
        child.name.casefold(): child
        for child in skills_root.iterdir()
        if child.is_dir()
    }
    existing_names = {
        str(skill.get("name", "")).strip().casefold()
        for skill in discover_skills(include_disabled=True)
        if str(skill.get("name", "")).strip()
    }

    copied: list[str] = []
    skipped: list[str] = []
    invalid: list[str] = []

    for source_dir in sorted(source_root.iterdir(), key=lambda path: path.name.casefold()):
        if not source_dir.is_dir():
            continue

        skill_file = _find_skill_file(source_dir)
        if skill_file is None:
            invalid.append(source_dir.name)
            continue

        try:
            skill_text = skill_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            skill_text = ""
        frontmatter, _ = _extract_frontmatter(skill_text)
        skill_name = (frontmatter.get("name") or source_dir.name).strip()

        folder_key = source_dir.name.casefold()
        name_key = skill_name.casefold()
        existing_dir = existing_folders.get(folder_key)
        if existing_dir is not None:
            # Bundled files are application-managed. Refresh them on upgrade while
            # preserving the user's enable state and any unrelated extra files.
            shutil.copytree(source_dir, existing_dir, dirs_exist_ok=True)
            skipped.append(source_dir.name)
            continue
        if name_key in existing_names:
            skipped.append(source_dir.name)
            continue

        destination = skills_root / source_dir.name
        shutil.copytree(source_dir, destination)
        set_skill_enabled(source_dir.name, True)
        existing_folders[folder_key] = destination
        existing_names.add(name_key)
        copied.append(source_dir.name)

    return {"copied": copied, "skipped": skipped, "invalid": invalid}


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
    builtin_folders = _builtin_skill_folders()
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
                "builtin": child.name.casefold() in builtin_folders,
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

    def _append_chunk(title: str, content: str) -> None:
        if not content:
            return
        payload = f"\n## {title}\n{content.strip()}\n"
        chunks.append(payload)

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
        "Discovered local skills (auto-scanned from wence_data/project/skills with SKILL.md):",
    ]
    for s in skills:
        desc = s["description"].strip() or "(no description)"
        lines.append(f"- {s['name']} (folder: {s['folder']}): {desc}")

    lines.extend(
        [
            "When user intent matches a skill, call load_skill_context(skill_name) with the skill folder name.",
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
    """Install skill package from zip file into wence_data/project/skills."""
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

        existing_dir = next(
            (
                child
                for child in skills_root.iterdir()
                if child.is_dir() and child.name.casefold() == safe_folder_name.casefold()
            ),
            None,
        )
        if existing_dir is not None:
            raise SkillAlreadyExistsError(f"Skill 已存在：{existing_dir.name}。请先删除该同名 Skill，再重新上传。")

        try:
            uploaded_skill_text = skill_md_candidates[0].read_text(encoding="utf-8", errors="ignore")
        except Exception:
            uploaded_skill_text = ""
        uploaded_frontmatter, _ = _extract_frontmatter(uploaded_skill_text)
        uploaded_name = (uploaded_frontmatter.get("name") or safe_folder_name).strip()
        existing_skill = next(
            (
                skill
                for skill in discover_skills(include_disabled=True)
                if str(skill.get("name", "")).strip().casefold() == uploaded_name.casefold()
            ),
            None,
        )
        if existing_skill is not None:
            raise SkillAlreadyExistsError(f"Skill 已存在：{existing_skill['name']}。请先删除该同名 Skill，再重新上传。")

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


def open_skill_directory(folder: str) -> Path:
    """Open an installed skill directory in the platform file manager."""
    folder_key = _validate_folder_key(folder)
    skills_root = _skills_root().resolve()
    target_dir = (skills_root / folder_key).resolve()
    if target_dir.parent != skills_root or not target_dir.is_dir():
        raise FileNotFoundError(f"Skill folder not found: {folder_key}")

    if sys.platform == "win32":
        os.startfile(str(target_dir))
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(target_dir)])
    else:
        subprocess.Popen(
            ["xdg-open", str(target_dir)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    return target_dir
