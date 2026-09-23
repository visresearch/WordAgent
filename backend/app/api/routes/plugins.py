"""Installable Python plugin catalog and background operations."""

from __future__ import annotations

import re
import shutil
import tempfile
import threading
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.services.plugins import manager

router = APIRouter()
_lock = threading.Lock()
_operations: dict[str, dict] = {}
_busy: set[str] = set()


class InstallRequest(BaseModel):
    source: str = Field(min_length=1, max_length=150)


@router.get("/plugins")
async def list_plugins():
    with _lock:
        busy = list(_busy)
        running = [dict(item, logs=list(item["logs"])) for item in _operations.values() if item["status"] == "running"]
    return {"plugins": manager.discover_plugins(), "busy": busy, "operations": running}


def _start(plugin_id: str, action: str, source: str = "", package_file: Path | None = None) -> dict:
    with _lock:
        if plugin_id in _busy:
            raise HTTPException(status_code=409, detail="Plugin operation already running")
        if len(_operations) >= 100:
            for old_id, old in list(_operations.items()):
                if old["status"] != "running":
                    del _operations[old_id]
                    if len(_operations) < 100:
                        break
        _busy.add(plugin_id)
        operation_id = str(uuid.uuid4())
        _operations[operation_id] = {
            "id": operation_id,
            "pluginId": plugin_id,
            "action": action,
            "status": "running",
            "logs": [],
            "error": "",
        }

    def run():
        def log(line):
            print(f"[plugin:{plugin_id}] {line}", flush=True)
            with _lock:
                _operations[operation_id]["logs"].append(str(line))
                _operations[operation_id]["logs"] = _operations[operation_id]["logs"][-400:]

        error = ""
        try:
            if action == "install":
                manager.install_plugin(source, log, package_file)
            else:
                manager.remove_plugin(plugin_id, log)
        except Exception as exc:
            error = str(exc)
            log(error)
        finally:
            if package_file:
                shutil.rmtree(package_file.parent, ignore_errors=True)
            with _lock:
                _busy.discard(plugin_id)
                _operations[operation_id]["status"] = "failed" if error else "completed"
                _operations[operation_id]["error"] = error

    threading.Thread(target=run, daemon=True, name=f"plugin-{action}-{plugin_id}").start()
    return {"operationId": operation_id, "pluginId": plugin_id}


@router.post("/plugins/install")
async def install_plugin(payload: InstallRequest):
    try:
        plugin_id, _package = manager._parse_source(payload.source.strip())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if plugin_id in {item["id"] for item in manager.installed_plugins()}:
        raise HTTPException(status_code=409, detail="Plugin is already installed")
    return _start(plugin_id, "install", payload.source.strip())


@router.post("/plugins/upload")
async def upload_plugin(file: UploadFile = File(...)):
    name = Path(file.filename or "").name
    if not re.fullmatch(r"[A-Za-z0-9_.-]+\.whl", name):
        raise HTTPException(status_code=400, detail="Upload a Python .whl file")
    package_name = name.split("-", 1)[0].replace("_", "-")
    try:
        plugin_id, _package = manager._parse_source(package_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if plugin_id in {item["id"] for item in manager.installed_plugins()}:
        raise HTTPException(status_code=409, detail="Plugin is already installed")
    temp_dir = Path(tempfile.mkdtemp(prefix="wordagent-plugin-upload-"))
    package_file = temp_dir / name
    try:
        size = 0
        with package_file.open("wb") as target:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > 150 * 1024 * 1024:
                    raise HTTPException(status_code=413, detail="Plugin wheel exceeds 150 MB")
                target.write(chunk)
        return _start(plugin_id, "install", package_name, package_file)
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise


@router.delete("/plugins/{plugin_id}")
async def delete_plugin(plugin_id: str):
    if plugin_id not in {item["id"] for item in manager.installed_plugins()}:
        raise HTTPException(status_code=404, detail="Plugin is not installed")
    return _start(plugin_id, "remove")


@router.get("/plugins/operations/{operation_id}")
async def get_operation(operation_id: str):
    with _lock:
        operation = _operations.get(operation_id)
        if operation is None:
            raise HTTPException(status_code=404, detail="Operation not found")
        return dict(operation, logs=list(operation["logs"]))
