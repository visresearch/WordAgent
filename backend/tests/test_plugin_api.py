import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import plugins


def test_plugin_list_uses_the_agent_catalog_github_folder(monkeypatch):
    app = FastAPI()
    app.include_router(plugins.router)
    monkeypatch.setattr(plugins.manager, "installed_plugins", lambda: [])
    response = TestClient(app).get("/plugins")
    assert response.status_code == 200
    item = response.json()["plugins"][0]
    assert item["id"] == "ocr"
    assert item["installed"] is False
    assert item["source"] == plugins.manager.CATALOG[0]["source"]
    assert "/backend/resources/plugins/wordagent-plugin-ocr" in item["source"]


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


def test_custom_github_url_is_passed_to_installer(monkeypatch):
    app = FastAPI()
    app.include_router(plugins.router)
    monkeypatch.setattr(plugins.manager, "installed_plugins", lambda: [])
    seen = []

    def install(source, log):
        seen.append(source)
        log("GitHub plugin installed")

    monkeypatch.setattr(plugins.manager, "install_plugin", install)
    with plugins._lock:
        plugins._operations.clear()
        plugins._busy.clear()

    client = TestClient(app)
    source = "https://github.com/owner/demo/tree/main/plugins/custom"
    response = client.post("/plugins/install", json={"source": source})
    assert response.status_code == 200
    operation_id = response.json()["operationId"]
    for _ in range(100):
        operation = client.get(f"/plugins/operations/{operation_id}").json()
        if operation["status"] != "running":
            break
        time.sleep(0.01)
    assert operation["status"] == "completed"
    assert seen == [source]


@pytest.mark.parametrize("source", ["wordagent-plugin-demo==1.0.0", "https://example.com/plugin"])
def test_custom_install_rejects_non_github_sources(source):
    app = FastAPI()
    app.include_router(plugins.router)
    response = TestClient(app).post("/plugins/install", json={"source": source})
    assert response.status_code == 400
    assert "GitHub" in response.json()["detail"]


@pytest.mark.parametrize("failure", [ValueError("Not a compatible WordAgent plugin"), AssertionError()])
def test_failed_install_exposes_reason_and_releases_busy_state(monkeypatch, failure):
    app = FastAPI()
    app.include_router(plugins.router)
    monkeypatch.setattr(plugins.manager, "installed_plugins", lambda: [])

    def fail(source, log):
        log("Checking Python plugin project")
        raise failure

    monkeypatch.setattr(plugins.manager, "install_plugin", fail)
    client = TestClient(app)
    response = client.post("/plugins/install", json={"source": "https://github.com/owner/incompatible"})
    operation_id = response.json()["operationId"]
    for _ in range(100):
        operation = client.get(f"/plugins/operations/{operation_id}").json()
        if operation["status"] != "running":
            break
        time.sleep(0.01)
    assert operation["status"] == "failed"
    assert operation["error"] == (str(failure) or type(failure).__name__)
    assert "Checking Python plugin project" in operation["logs"]
    assert response.json()["pluginId"] not in client.get("/plugins").json()["busy"]
