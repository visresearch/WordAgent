"""Word and WPS share MCP discovery, with explicit and safe host routing."""

from concurrent.futures import ThreadPoolExecutor
from importlib import reload
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from test_wps_mcp import _mcp_request, _test_app, runtime, wps_mcp


@pytest.fixture(autouse=True)
def fresh_mcp_module():
    # The SDK session manager supports exactly one lifespan per instance.
    reload(wps_mcp)


def _roundtrip(client, socket, tool, arguments):
    with ThreadPoolExecutor(max_workers=1) as executor:
        call = executor.submit(_mcp_request, client, "tools/call", {"name": tool, "arguments": arguments})
        request = socket.receive_json()
        socket.send_json({"requestId": request["requestId"], "result": {"success": True, "host": "word"}})
        result = call.result(timeout=5).json()["result"]
        assert not result["isError"]
        return request


def test_word_tool_discovery_and_all_seven_roundtrips(monkeypatch):
    monkeypatch.setattr(wps_mcp, "_local_websocket", lambda _: True)
    with TestClient(_test_app(), base_url="http://127.0.0.1:3880") as client:
        runtime.start()
        init = _mcp_request(
            client,
            "initialize",
            {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "Codex", "version": "1"},
            },
        ).json()["result"]
        assert init["serverInfo"]["name"] == "WordAgent"
        assert "Microsoft Word" in init["instructions"]
        for tool in _mcp_request(client, "tools/list").json()["result"]["tools"]:
            assert "host" in tool["inputSchema"]["properties"]
        style = ["Arial", 12, False, False, "none", None, "#000000", None, False, False, False]
        examples = {
            "read_document": {"mode": "lightweight", "startParaID": 123},
            "search_document": {"query": {"type": "paragraph", "filters": {"text": "hello"}}},
            "delete_document": {"paraIDs": [123]},
            "edit_document": {"paraID": 123, "runs": [{"text": "new", "rStyle": "rS_1"}], "styles": {"rS_1": style}},
            "insert_break": {"paraID": 123, "breakType": "wdPageBreak"},
            "generate_document": {"document": {"paragraphs": [], "styles": {}}, "insertParaID": 123},
            "create_document": {},
        }
        with client.websocket_connect("/api/mcp/bridge?host=word") as socket:
            for tool, args in examples.items():
                request = _roundtrip(client, socket, tool, {**args, "host": "word"})
                assert request["tool"] == tool
                assert "host" not in request["arguments"]
                if tool == "edit_document":
                    assert request["arguments"]["runs"][0]["rStyle"] == style
                    assert "styles" not in request["arguments"]
            # A Word-only connection is also selected for legacy calls without host.
            _roundtrip(client, socket, "create_document", {})
            result = _mcp_request(
                client,
                "tools/call",
                {
                    "name": "edit_document",
                    "arguments": {"host": "word", "paraID": 123, "runs": [{"text": "new", "rStyle": "missing"}]},
                },
            ).json()["result"]
            assert result["isError"]
            assert "styles" in result["content"][0]["text"]
        assert not wps_mcp.bridge.connections["word"]


def test_routing_never_falls_back_to_another_host_or_ambiguous_word_pane(monkeypatch):
    monkeypatch.setattr(wps_mcp, "_local_websocket", lambda _: True)
    with TestClient(_test_app(), base_url="http://127.0.0.1:3880") as client:
        runtime.start()
        with client.websocket_connect("/api/mcp/bridge") as wps_socket:
            result = _mcp_request(
                client, "tools/call", {"name": "create_document", "arguments": {"host": "word"}}
            ).json()["result"]
            assert result["isError"]
            assert "Microsoft Word 插件页面未连接" in result["content"][0]["text"]
            with client.websocket_connect("/api/mcp/bridge?host=word") as word_socket:
                result = _mcp_request(client, "tools/call", {"name": "create_document"}).json()["result"]
                assert result["isError"]
                assert "请指定 host" in result["content"][0]["text"]
                _roundtrip(client, word_socket, "create_document", {"host": "word"})
                _roundtrip(client, wps_socket, "create_document", {"host": "wps"})
                with client.websocket_connect("/api/mcp/bridge?host=word"):
                    result = _mcp_request(
                        client, "tools/call", {"name": "create_document", "arguments": {"host": "word"}}
                    ).json()["result"]
                    assert result["isError"]
                    assert "多个加载项侧栏连接" in result["content"][0]["text"]
                _roundtrip(client, word_socket, "create_document", {"host": "word"})


def test_word_errors_and_pending_calls_on_disconnect(monkeypatch):
    monkeypatch.setattr(wps_mcp, "_local_websocket", lambda _: True)
    with TestClient(_test_app(), base_url="http://127.0.0.1:3880") as client:
        runtime.start()
        with ThreadPoolExecutor(max_workers=1) as executor:
            with client.websocket_connect("/api/mcp/bridge?host=word") as socket:
                call = executor.submit(
                    _mcp_request, client, "tools/call", {"name": "read_document", "arguments": {"host": "word"}}
                )
                request = socket.receive_json()
                # Invalid / unrelated responses cannot complete the request.
                socket.send_json({"requestId": [], "result": {}})
                socket.send_json({"requestId": "unknown", "result": {}})
                socket.send_json({"requestId": request["requestId"], "error": "Office.js rejected the operation"})
                result = call.result(timeout=5).json()["result"]
                assert result["isError"]
                assert "Office.js rejected" in result["content"][0]["text"]
                call = executor.submit(
                    _mcp_request, client, "tools/call", {"name": "create_document", "arguments": {"host": "word"}}
                )
                socket.receive_json()
            result = call.result(timeout=5).json()["result"]
            assert result["isError"]
            assert "Microsoft Word 插件页面已断开连接" in result["content"][0]["text"]
        assert not wps_mcp.bridge.connections["word"]


def test_invalid_host_is_rejected(monkeypatch):
    monkeypatch.setattr(wps_mcp, "_local_websocket", lambda _: True)
    with TestClient(_test_app()) as client:
        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect("/api/mcp/bridge?host=unknown"):
                pass
        assert exc.value.code == 1008


@pytest.mark.parametrize(
    ("address", "origin", "allowed"),
    [
        ("127.0.0.1", "https://localhost:3000", True),
        ("::1", "http://127.0.0.1:3880", True),
        ("127.0.0.1", "https://untrusted.example", False),
        ("192.168.0.5", "https://localhost:3000", False),
    ],
)
def test_bridge_origin_checks(address, origin, allowed):
    socket = SimpleNamespace(client=SimpleNamespace(host=address), headers={"origin": origin})
    assert wps_mcp._local_websocket(socket) is allowed
