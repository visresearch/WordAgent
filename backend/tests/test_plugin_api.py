import time

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import plugins


def test_plugin_install_operation_exposes_logs_and_completion(monkeypatch):
    app = FastAPI()
    app.include_router(plugins.router)
    monkeypatch.setattr(plugins.manager, "installed_plugins", lambda: [])
    monkeypatch.setattr(plugins.manager, "discover_plugins", lambda: [{"id": "ocr", "installed": False}])
    monkeypatch.setattr(plugins.manager, "install_plugin", lambda source, log, package_file=None: log("models loaded"))
    with plugins._lock:
        plugins._operations.clear()
        plugins._busy.clear()

    client = TestClient(app)
    response = client.post("/plugins/install", json={"source": "ocr"})
    assert response.status_code == 200
    operation_id = response.json()["operationId"]
    for _ in range(100):
        operation = client.get(f"/plugins/operations/{operation_id}").json()
        if operation["status"] != "running":
            break
        time.sleep(0.01)
    assert operation["status"] == "completed"
    assert "models loaded" in operation["logs"]
    assert client.get("/plugins").json()["plugins"][0]["id"] == "ocr"


def test_custom_wheel_upload_passes_file_to_installer(monkeypatch):
    app = FastAPI()
    app.include_router(plugins.router)
    monkeypatch.setattr(plugins.manager, "installed_plugins", lambda: [])
    seen = []

    def install(source, log, package_file=None):
        seen.append((source, package_file.read_bytes()))
        log("wheel installed")

    monkeypatch.setattr(plugins.manager, "install_plugin", install)
    with plugins._lock:
        plugins._operations.clear()
        plugins._busy.clear()

    client = TestClient(app)
    response = client.post(
        "/plugins/upload", files={"file": ("wordagent_plugin_demo-0.1.0-py3-none-any.whl", b"wheel")}
    )
    assert response.status_code == 200
    operation_id = response.json()["operationId"]
    for _ in range(100):
        operation = client.get(f"/plugins/operations/{operation_id}").json()
        if operation["status"] != "running":
            break
        time.sleep(0.01)
    assert operation["status"] == "completed"
    assert seen == [("wordagent-plugin-demo", b"wheel")]
