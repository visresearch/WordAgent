"""MCP HTTP transport and the WPS WebSocket request bridge."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from importlib import import_module

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.services.mcp_runtime import runtime

wps_mcp = import_module("app.services.mcp-server")


HEADERS = {"accept": "application/json, text/event-stream", "content-type": "application/json"}


def _test_app():
    @asynccontextmanager
    async def lifespan(_app):
        async with wps_mcp.mcp.session_manager.run():
            runtime.set_ready(True)
            try:
                yield
            finally:
                runtime.set_ready(False)

    app = FastAPI(lifespan=lifespan)
    app.include_router(wps_mcp.router, prefix="/api")
    app.mount("/mcp", wps_mcp.mcp_app)
    return app


def _mcp_request(client, method, params=None):
    return client.post(
        "/mcp/",
        headers=HEADERS,
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}},
    )


def test_mcp_lists_tools_and_roundtrips_through_wps_bridge(monkeypatch):
    # TestClient's simulated WebSocket client address is 'testclient'.
    monkeypatch.setattr(wps_mcp, "_local_websocket", lambda _socket: True)
    with TestClient(_test_app(), base_url="http://127.0.0.1:3880") as client:
        assert _mcp_request(client, "tools/list").status_code == 503
        assert runtime.start()
        initialized = _mcp_request(
            client,
            "initialize",
            {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "Codex", "version": "1"}},
        )
        assert initialized.status_code == 200
        assert runtime.snapshot()["clients"][0]["name"] == "Codex"
        listed = _mcp_request(client, "tools/list")
        assert {tool["name"] for tool in listed.json()["result"]["tools"]} == {
            "delete_document", "edit_document", "create_document", "insert_break",
            "generate_document", "read_document", "search_document",
        }
        disconnected = _mcp_request(client, "tools/call", {"name": "create_document", "arguments": {}})
        assert disconnected.json()["result"]["isError"] is True
        assert "WPS 插件页面未连接" in disconnected.json()["result"]["content"][0]["text"]
        with client.websocket_connect("/api/mcp/bridge") as socket:
            with ThreadPoolExecutor(max_workers=1) as executor:
                call = executor.submit(
                    _mcp_request, client, "tools/call", {"name": "create_document", "arguments": {}}
                )
                request = socket.receive_json()
                assert request["tool"] == "create_document"
                assert request["arguments"] == {}
                socket.send_json({"requestId": request["requestId"], "result": {"success": True, "documentId": 42}})
                response = call.result(timeout=5).json()["result"]
                assert response["isError"] is False
                assert '"documentId": 42' in response["content"][0]["text"]
        runtime.stop()
        assert runtime.snapshot()["clients"] == []
        assert _mcp_request(client, "tools/list").status_code == 503
