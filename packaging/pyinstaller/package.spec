# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller build spec for WordAgent.

The spec lives under packaging/ so all paths are resolved from the repository
root instead of the current working directory. GitHub Actions can therefore run
PyInstaller from backend/ while still using this single shared spec.
"""

import os
import subprocess

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

spec_dir = os.path.abspath(SPECPATH)
repo_root = os.path.abspath(os.path.join(spec_dir, "..", ".."))
backend_dir = os.path.join(repo_root, "backend")
frontend_dir = os.path.join(repo_root, "frontend")
packaging_dir = os.path.join(repo_root, "packaging")


def _release_version():
    version = (os.environ.get("APP_VERSION") or "").strip()
    if version:
        return version

    ref_type = (os.environ.get("GITHUB_REF_TYPE") or "").strip().lower()
    ref_name = (os.environ.get("GITHUB_REF_NAME") or "").strip()
    if ref_type == "tag" and ref_name:
        return ref_name

    try:
        return subprocess.check_output(
            ["git", "describe", "--tags"],
            cwd=repo_root,
            text=True,
        ).strip()
    except Exception:
        return ""


def _data(src, dst, required=True):
    if os.path.exists(src):
        return (src, dst)
    if required:
        raise FileNotFoundError(f"Required packaging input is missing: {src}")
    return None


version_value = _release_version()
generated_env_path = ""
if version_value:
    os.environ.setdefault("APP_VERSION", version_value)
    generated_env_dir = os.path.join(spec_dir, "build", "runtime_env")
    generated_env_path = os.path.join(generated_env_dir, ".env")
    os.makedirs(generated_env_dir, exist_ok=True)
    with open(generated_env_path, "w", encoding="utf-8") as f:
        f.write(f"APP_VERSION={version_value}\n")

datas = [
    _data(os.path.join(backend_dir, "README.md"), "."),
    _data(os.path.join(backend_dir, "app"), "app"),
    _data(os.path.join(frontend_dir, "wps_word_plugin", "dist"), "frontend"),
    _data(os.path.join(frontend_dir, "microsoft_word_plugin", "dist"), "msoffice"),
]

optional_datas = [
    _data(os.path.join(backend_dir, "gui", "resources"), "gui/resources", required=False),
]
datas.extend(item for item in optional_datas if item)
if generated_env_path:
    datas.append((generated_env_path, "."))

hiddenimports = [
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "fastapi",
    "fastapi.responses",
    "starlette",
    "starlette.middleware",
    "starlette.middleware.cors",
    "pydantic",
    "pydantic_core",
    "pydantic_settings",
    "sqlalchemy",
    "sqlalchemy.ext.asyncio",
    "aiosqlite",
    "openai",
    "httpx",
    "anyio",
    "langchain",
    "langchain_core",
    "langchain_openai",
    "langchain_anthropic",
    "langchain_community",
    "langgraph",
    "dotenv",
    "rapidocr_onnxruntime",
    "onnxruntime",
    "PySide6",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "app",
    "app.main",
    "app.core",
    "app.core.config",
    "app.core.db",
    "app.api",
    "app.api.routes",
    "app.api.routes.chat",
    "app.api.routes.history",
    "app.api.routes.models",
    "app.api.routes.settings",
    "app.services",
    "app.services.agent",
    "app.services.chat_history",
    "app.services.llm_client",
    "app.models",
    "app.models.chat",
    "app.models.db_models",
    "app.models.doc",
    "gui",
    "gui.main",
]

hiddenimports += collect_submodules("langchain")
hiddenimports += collect_submodules("langchain_core")
hiddenimports += collect_submodules("langchain_openai")
hiddenimports += collect_submodules("langgraph")

a = Analysis(
    [os.path.join(backend_dir, "main.py")],
    pathex=[backend_dir],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "matplotlib",
        "seaborn",
        "tkinter",
        "jupyter",
        "notebook",
        "tensorflow",
        "torch",
        "torchvision",
        "keras",
        "jax",
        "evaluation",
        "babel",
        "tqdm",
        "sphinx",
        "docutils",
        "openpyxl",
        "pygraphviz",
        "fsspec",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

icon_path = os.path.join(packaging_dir, "robot.ico")

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="wence_ai",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path if os.path.exists(icon_path) else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="wence_ai",
)
