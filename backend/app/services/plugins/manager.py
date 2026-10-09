"""Discover, download and invoke isolated plugin packages from the agent catalog."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, unquote, urlsplit
from urllib.request import Request, urlopen

import tomllib
from packaging.specifiers import InvalidSpecifier, SpecifierSet

from app.core.config import get_wence_data_dir

_PACKAGE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*(?:==[A-Za-z0-9][A-Za-z0-9._+-]*)?$")


def _load_catalog() -> tuple[dict, ...]:
    catalog_file = Path(__file__).resolve().parents[1] / "agent" / "plugin.json"
    data = json.loads(catalog_file.read_text(encoding="utf-8"))
    plugins = data.get("plugins") if isinstance(data, dict) else None
    if not isinstance(plugins, list):
        raise ValueError("agent/plugin.json must contain a plugins list")
    ids = set()
    packages = set()
    for item in plugins:
        if not isinstance(item, dict) or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", str(item.get("id", ""))):
            raise ValueError("Invalid plugin catalog ID")
        package = str(item.get("package", ""))
        if not _PACKAGE_RE.fullmatch(package) or not package.startswith("wordagent-plugin-") or "==" in package:
            raise ValueError("Invalid plugin catalog package")
        if item["id"] in ids or package in packages:
            raise ValueError("Duplicate plugin catalog entry")
        if not isinstance(item.get("capabilities"), list) or not item.get("source"):
            raise ValueError("Plugin catalog entries require capabilities and a GitHub folder source")
        ids.add(item["id"])
        packages.add(package)
    return tuple(plugins)


CATALOG = _load_catalog()


def plugins_dir() -> Path:
    if sys.platform == "win32" and not os.environ.get("WENCE_DATA_DIR"):
        return Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "WenCeAI" / "plugins"
    return get_wence_data_dir() / "plugins"


def _plugin_dir(plugin_id: str) -> Path:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", plugin_id):
        raise ValueError("Invalid plugin ID")
    return plugins_dir() / plugin_id


def _python(plugin_id: str) -> Path:
    venv = _plugin_dir(plugin_id) / "venv"
    return venv / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


def _runner() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "app" / "services" / "plugins" / "runner.py"
    return Path(__file__).with_name("runner.py")


def _uv() -> str:
    if getattr(sys, "frozen", False):
        bundled = Path(sys._MEIPASS) / "tools" / ("uv.exe" if sys.platform == "win32" else "uv")
        if bundled.is_file():
            return str(bundled)
    found = shutil.which("uv")
    if not found:
        raise RuntimeError("uv executable was not found")
    return found


def _env() -> dict[str, str]:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    if "LD_LIBRARY_PATH_ORIG" in env:
        env["LD_LIBRARY_PATH"] = env.pop("LD_LIBRARY_PATH_ORIG")
    env["UV_NO_PROGRESS"] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env


def _flags() -> int:
    return subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


def _run(command: list[str], log: Callable[[str], None]) -> str:
    log("$ " + " ".join(command))
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=_env(),
        creationflags=_flags(),
    )
    assert process.stdout is not None
    lines = []
    for line in process.stdout:
        line = line.rstrip()
        lines.append(line)
        log(line)
    if process.wait():
        raise RuntimeError(lines[-1] if lines else "Plugin command failed")
    return "\n".join(lines)


def _result(output: str) -> dict:
    for line in reversed(output.splitlines()):
        if line.startswith("PLUGIN_RESULT:"):
            result = json.loads(line[len("PLUGIN_RESULT:") :])
            if not isinstance(result, dict):
                raise RuntimeError("Plugin result must be a JSON object")
            return result
    raise RuntimeError("Plugin returned no result")


def _github_folder(source: str) -> tuple[str, str, str, str]:
    url = urlsplit(source)
    parts = unquote(url.path).strip("/").split("/")
    if (
        url.scheme != "https"
        or url.netloc.lower() != "github.com"
        or len(parts) < 2
        or (len(parts) != 2 and (len(parts) < 4 or parts[2] != "tree"))
    ):
        raise ValueError("Enter a GitHub repository or plugin folder URL (https://github.com/owner/repo)")
    if any(not part or part in {".", ".."} or any(char in part for char in "\\:\x00\r\n") for part in parts):
        raise ValueError("Invalid GitHub plugin folder path")
    if not re.fullmatch(r"[A-Za-z0-9-]+", parts[0]) or not re.fullmatch(r"[A-Za-z0-9_.-]+", parts[1]):
        raise ValueError("Invalid GitHub repository name")
    repo = parts[1].removesuffix(".git")
    if not repo or repo in {".", ".."}:
        raise ValueError("Invalid GitHub repository name")
    return parts[0].lower(), repo.lower(), parts[3] if len(parts) >= 4 else "", "/".join(parts[4:])


def _download_plugin_source(item: dict, log: Callable[[str], None], temp_dir: Path) -> Path:
    owner, repo, default_ref, folder = _github_folder(item["source"])
    release = os.environ.get("APP_VERSION", "")
    use_release = any(item["id"] == catalog["id"] for catalog in CATALOG)
    refs = [release, default_ref] if use_release and re.fullmatch(r"v[0-9][A-Za-z0-9._-]*", release) else [default_ref]
    refs = list(dict.fromkeys(refs))
    source = temp_dir / item["package"]

    def download_directory(repo_path: str, target_dir: Path, ref: str) -> None:
        api_url = (
            f"https://api.github.com/repos/{quote(owner, safe='')}/{quote(repo, safe='')}"
            f"/contents/{quote(repo_path, safe='/')}"
        )
        if ref:
            api_url += f"?ref={quote(ref, safe='')}"
        request = Request(api_url, headers={"User-Agent": "WordAgent", "Accept": "application/vnd.github+json"})
        with urlopen(request, timeout=30) as response:
            entries = json.loads(response.read())
        if not isinstance(entries, list):
            raise ValueError("GitHub plugin source is not a directory")
        target_dir.mkdir(parents=True, exist_ok=True)
        for entry in entries:
            name = entry.get("name", "")
            if not name or name in {".", ".."} or any(char in name for char in "/\\:"):
                raise ValueError("Invalid file name in GitHub plugin source")
            child_path = f"{repo_path}/{name}" if repo_path else name
            if entry.get("path") != child_path:
                raise ValueError("GitHub plugin entry is outside its source folder")
            target = target_dir / name
            if entry["type"] == "dir":
                download_directory(child_path, target, ref)
            elif entry["type"] == "file" and not entry.get("submodule_git_url"):
                download_url = entry.get("download_url") or ""
                parsed = urlsplit(download_url)
                if parsed.scheme != "https" or parsed.netloc != "raw.githubusercontent.com":
                    raise ValueError("Invalid GitHub plugin download URL")
                relative = child_path[len(folder) + 1 :] if folder else child_path
                log(f"Downloading {relative} ({ref or 'default branch'})")
                with (
                    urlopen(Request(download_url, headers={"User-Agent": "WordAgent"}), timeout=30) as response,
                    target.open("wb") as output,
                ):
                    shutil.copyfileobj(response, output)
            else:
                raise ValueError("Plugin source may contain only files and directories")

    for ref in refs:
        try:
            log(f"Downloading plugin {item['id']} from {item['source']} ({ref or 'default branch'})")
            download_directory(folder, source, ref)
            return source
        except HTTPError as exc:
            shutil.rmtree(source, ignore_errors=True)
            if exc.code != 404 or ref == refs[-1]:
                if exc.code == 404:
                    hint = " Publish the resources/plugins folder before installation." if use_release else ""
                    raise RuntimeError(
                        f"Plugin repository or folder not found on GitHub: {item['source']}.{hint}"
                    ) from exc
                raise
            log(f"Plugin source unavailable at {ref}; trying {default_ref}")
    raise RuntimeError("Plugin source is unavailable")


def _parse_source(source: str) -> tuple[str, str]:
    source = source.strip()
    for item in CATALOG:
        if source in (item["id"], item["package"]):
            return item["id"], item["source"]
    owner, repo, ref, folder = _github_folder(source)
    source = f"https://github.com/{owner}/{repo}"
    if ref:
        source += f"/tree/{quote(ref, safe='')}"
        if folder:
            source += f"/{quote(folder, safe='/')}"
    for item in CATALOG:
        if (owner, repo, ref, folder) == _github_folder(item["source"]):
            return item["id"], source
    label = re.sub(r"[^a-z0-9-]+", "-", folder.rsplit("/", 1)[-1].lower() if folder else repo).strip("-")
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()[:12]
    return f"github-{owner}-{label[:50] or 'plugin'}-{digest}", source


def _validate_plugin_source(source: Path, log: Callable[[str], None]) -> dict:
    log("Checking Python plugin project")
    pyproject = source / "pyproject.toml"
    if not pyproject.is_file():
        raise ValueError(
            "Not an installable Python plugin: pyproject.toml is missing. Select the plugin project folder."
        )
    try:
        with pyproject.open("rb") as file:
            data = tomllib.load(file)
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(f"Invalid Python plugin pyproject.toml: {exc}") from exc
    project = data.get("project")
    if not isinstance(project, dict) or not isinstance(project.get("name"), str):
        raise ValueError("Python plugin pyproject.toml must declare [project].name")
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?", project["name"]):
        raise ValueError("Invalid Python plugin project name")
    entries = project.get("entry-points", {})
    entries = entries.get("wordagent.plugins") if isinstance(entries, dict) else None
    if not isinstance(entries, dict) or not entries:
        raise ValueError(
            "Python project is not a compatible WordAgent plugin: wordagent.plugins entry point is missing"
        )
    for value in entries.values():
        if not isinstance(value, str) or not re.fullmatch(
            r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*:[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*", value
        ):
            raise ValueError("Invalid WordAgent plugin entry point; expected module:object")
    if not any(path.is_file() for path in source.rglob("*.py")):
        raise ValueError("Not a Python plugin: the project contains no .py program files")
    requirement = project.get("requires-python", "")
    if not isinstance(requirement, str):
        raise ValueError("Python plugin requires-python must be a version requirement string")
    try:
        SpecifierSet(requirement)
    except InvalidSpecifier as exc:
        raise ValueError(f"Invalid plugin Python version requirement: {requirement}") from exc
    return project


def installed_plugins() -> list[dict]:
    root = plugins_dir()
    if not root.exists():
        return []
    results = []
    for folder in root.iterdir():
        manifest = folder / "plugin.json"
        try:
            if manifest.is_file() and _python(folder.name).is_file():
                info = json.loads(manifest.read_text(encoding="utf-8"))
                if (
                    isinstance(info, dict)
                    and info.get("id") == folder.name
                    and isinstance(info.get("capabilities"), list)
                ):
                    results.append(info)
        except (OSError, ValueError, KeyError):
            continue
    return sorted(results, key=lambda item: item["id"])


def discover_plugins() -> list[dict]:
    installed = {item["id"]: item for item in installed_plugins()}
    catalog = [dict(item, installed=item["id"] in installed) for item in CATALOG]
    custom = [dict(item, installed=True) for key, item in installed.items() if key not in {c["id"] for c in CATALOG}]
    return catalog + custom


def install_plugin(source: str, log: Callable[[str], None] = print) -> dict:
    source = source.strip()
    plugin_id, github_source = _parse_source(source)
    root = _plugin_dir(plugin_id)
    if (root / "plugin.json").is_file():
        raise ValueError("Plugin is already installed")
    root.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(root / "venv", ignore_errors=True)
    try:
        with tempfile.TemporaryDirectory(prefix="wordagent-plugin-") as temp:
            catalog_item = next((item for item in CATALOG if item["id"] == plugin_id), None)
            item = catalog_item or {"id": plugin_id, "package": plugin_id, "source": github_source}
            install_source = _download_plugin_source(item, log, Path(temp))
            project = _validate_plugin_source(install_source, log)
            uv = _uv()
            _run([uv, "venv", str(root / "venv"), "--python", "3.11"], log)
            runtime = _result(
                _run([str(_python(plugin_id)), str(_runner()), "--validate-source", str(install_source)], log)
            )
            requirement = project.get("requires-python", "")
            if not SpecifierSet(requirement).contains(runtime["pythonVersion"]):
                raise ValueError(
                    f"Plugin requires Python {requirement}, but the plugin environment uses Python {runtime['pythonVersion']}"
                )
            log("Installing Python plugin and dependencies")
            _run([uv, "pip", "install", "--no-cache", "--python", str(_python(plugin_id)), str(install_source)], log)
            log("Checking WordAgent plugin interface and compatibility")
            info = _result(_run([str(_python(plugin_id)), str(_runner()), "--inspect"], log))
            log("Running plugin self-check")
            checked = _result(_run([str(_python(plugin_id)), str(_runner()), "--check"], log))
            if checked.get("ready") is not True:
                raise RuntimeError("Plugin self-check did not report a ready state")
        if not info.get("capabilities") or not isinstance(info["capabilities"], list):
            raise ValueError("Plugin declares no capabilities")
        info = {
            "id": plugin_id,
            "source": github_source,
            "package": project["name"],
            "name": info["name"],
            "description": info["description"],
            "capabilities": info["capabilities"],
        }
        (root / "plugin.json").write_text(json.dumps(info, ensure_ascii=False), encoding="utf-8")
        log(f"Plugin {plugin_id} is ready")
        return info
    except Exception:
        shutil.rmtree(root, ignore_errors=True)
        raise


def remove_plugin(plugin_id: str, log: Callable[[str], None] = print) -> None:
    root = _plugin_dir(plugin_id)
    if not root.exists():
        raise FileNotFoundError(plugin_id)
    (root / "plugin.json").unlink(missing_ok=True)
    log(f"Removing {plugin_id}")
    shutil.rmtree(root)
    log(f"Removed {plugin_id}")


def has_capability(capability: str) -> bool:
    return any(capability in item.get("capabilities", []) for item in installed_plugins())


def invoke_capability(capability: str, payload: dict) -> dict:
    plugins = [item for item in installed_plugins() if capability in item.get("capabilities", [])]
    if not plugins:
        raise RuntimeError(f"Plugin capability {capability} is not installed. Install it from WPS Settings > Plugins.")
    item = plugins[0]
    result = subprocess.run(
        [str(_python(item["id"])), str(_runner()), capability, json.dumps(payload, ensure_ascii=False)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        env=_env(),
        creationflags=_flags(),
        check=False,
    )
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout).strip()[-2000:] or "Plugin failed")
    return _result(result.stdout)


def recognize_image(path: Path) -> str:
    return str(invoke_capability("ocr", {"path": str(path)})["text"])
