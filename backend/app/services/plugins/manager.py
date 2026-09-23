"""Discover, install and invoke isolated uv Python packages."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from urllib.request import Request, urlopen

from app.core.config import get_wence_data_dir

CATALOG = (
    {
        "id": "ocr",
        "name": "OCR",
        "description": "Read text in image files for language models without vision support.",
        "package": "wordagent-plugin-ocr",
        "capabilities": ["ocr"],
    },
)
_PACKAGE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*(?:==[A-Za-z0-9][A-Za-z0-9._+-]*)?$")
_OCR_FILES = (
    "pyproject.toml",
    "src/wordagent_plugin_ocr/__init__.py",
    "src/wordagent_plugin_ocr/plugin.py",
)
_OCR_REMOTE = (
    "https://raw.githubusercontent.com/visresearch/WordAgent/{ref}/backend/app/services/plugins/wordagent-plugin-ocr"
)


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
            return json.loads(line[len("PLUGIN_RESULT:") :])
    raise RuntimeError("Plugin returned no result")


def _ocr_source(log: Callable[[str], None], temp_dir: Path) -> Path:
    local = Path(__file__).parent / "wordagent-plugin-ocr"
    if local.is_dir():
        return local
    release = os.environ.get("APP_VERSION", "")
    refs = [release, "master"] if re.fullmatch(r"v[0-9][A-Za-z0-9._-]*", release) else ["master"]
    for ref in refs:
        source = temp_dir / "wordagent-plugin-ocr"
        try:
            for name in _OCR_FILES:
                target = source / name
                target.parent.mkdir(parents=True, exist_ok=True)
                url = f"{_OCR_REMOTE.format(ref=ref)}/{name}"
                log(f"Downloading {name} ({ref})")
                with urlopen(Request(url, headers={"User-Agent": "WordAgent"}), timeout=30) as response:
                    target.write_bytes(response.read())
            return source
        except OSError:
            shutil.rmtree(source, ignore_errors=True)
            if ref == refs[-1]:
                raise
            log(f"Plugin source unavailable at {ref}; trying master")
    raise RuntimeError("OCR plugin source is unavailable")


def _parse_source(source: str) -> tuple[str, str]:
    if source == "ocr":
        return "ocr", CATALOG[0]["package"]
    if not _PACKAGE_RE.fullmatch(source):
        raise ValueError("Enter a Python package name, optionally with ==version")
    package = source.split("==", 1)[0].lower().replace("_", "-").replace(".", "-")
    if not package.startswith("wordagent-plugin-"):
        raise ValueError("Custom packages must use the wordagent-plugin- prefix")
    if package == "wordagent-plugin-ocr":
        return "ocr", source
    return package, source


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


def install_plugin(source: str, log: Callable[[str], None] = print, package_file: Path | None = None) -> dict:
    plugin_id, package = _parse_source(source.strip())
    root = _plugin_dir(plugin_id)
    if (root / "plugin.json").is_file():
        raise ValueError("Plugin is already installed")
    root.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(root / "venv", ignore_errors=True)
    try:
        with tempfile.TemporaryDirectory(prefix="wordagent-plugin-") as temp:
            install_source = (
                str(package_file)
                if package_file
                else (str(_ocr_source(log, Path(temp))) if source == "ocr" else package)
            )
            uv = _uv()
            _run([uv, "venv", str(root / "venv"), "--python", "3.11"], log)
            _run([uv, "pip", "install", "--no-cache", "--python", str(_python(plugin_id)), install_source], log)
            info = _result(_run([str(_python(plugin_id)), str(_runner()), "--inspect"], log))
            _result(_run([str(_python(plugin_id)), str(_runner()), "--check"], log))
        if not info.get("capabilities") or not isinstance(info["capabilities"], list):
            raise ValueError("Plugin declares no capabilities")
        info = {
            "id": plugin_id,
            "source": source,
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
