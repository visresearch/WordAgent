import asyncio
import json
import unittest
from unittest.mock import patch

import httpx
from fastapi import FastAPI
from pydantic import ValidationError

from app.api.routes import settings
from app.api.routes.settings import UserSettings


class UserSettingsTemperatureTests(unittest.TestCase):
    def test_temperature_defaults_to_half(self):
        self.assertEqual(UserSettings().temperature, 0.5)

    def test_temperature_accepts_range_boundaries(self):
        self.assertEqual(UserSettings(temperature=0).temperature, 0)
        self.assertEqual(UserSettings(temperature=1).temperature, 1)

    def test_temperature_rejects_values_outside_range(self):
        for value in (-0.01, 1.01):
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    UserSettings(temperature=value)


def initialize_response(request):
    body = json.loads(request.content)
    return {
        "jsonrpc": "2.0",
        "id": body["id"],
        "result": {
            "protocolVersion": body["params"]["protocolVersion"],
            "capabilities": {},
            "serverInfo": {"name": "test-mcp", "version": "1.0"},
        },
    }


class EventStream(httpx.AsyncByteStream):
    """Keep a legacy SSE channel open while POST responses arrive on it."""

    def __init__(self):
        self.events = asyncio.Queue()
        self.closed = False

    async def __aiter__(self):
        while True:
            yield await self.events.get()

    async def aclose(self):
        self.closed = True


class MCPConnectionTests(unittest.IsolatedAsyncioTestCase):
    async def run_request(self, handler, config=None):
        config = {"url": "https://mcp.example/private-token/mcp", "timeout": 0.5, **(config or {})}
        client_class = httpx.AsyncClient
        clients = []

        def create_client(**kwargs):
            client = client_class(transport=httpx.MockTransport(handler), **kwargs)
            clients.append(client)
            return client

        with patch.object(settings.httpx, "AsyncClient", side_effect=create_client):
            result = await settings.test_mcp_server(settings.MCPServerTestRequest(name="test-mcp", config=config))
        self.assertTrue(clients)
        self.assertTrue(all(client.is_closed for client in clients))
        return result

    async def test_streamable_http_initializes_with_post_even_when_get_and_delete_return_405(self):
        for transport in (None, "http", "streamable_http", "streamable-http"):
            with self.subTest(transport=transport):
                requests = []

                def respond(request, requests=requests):
                    requests.append(request)
                    if request.method in ("GET", "DELETE"):
                        return httpx.Response(405)
                    self.assertEqual(request.method, "POST")
                    self.assertIn("application/json", request.headers["accept"])
                    self.assertIn("text/event-stream", request.headers["accept"])
                    body = json.loads(request.content)
                    if body["method"] == "initialize":
                        return httpx.Response(
                            200, json=initialize_response(request), headers={"Mcp-Session-Id": "test-session"}
                        )
                    self.assertEqual(body["method"], "notifications/initialized")
                    self.assertEqual(request.headers["mcp-session-id"], "test-session")
                    self.assertTrue(request.headers["mcp-protocol-version"])
                    return httpx.Response(202)

                config = {"type": transport} if transport else {}
                result = await self.run_request(respond, config)
                self.assertTrue(result["success"], result)
                self.assertEqual(requests[0].method, "POST")
                self.assertEqual(json.loads(requests[0].content)["method"], "initialize")
                self.assertIn("DELETE", [request.method for request in requests])

    async def test_streamable_http_accepts_sse_post_response_and_forwards_auth_headers(self):
        def respond(request):
            self.assertEqual(request.method, "POST")
            self.assertEqual(request.headers["authorization"], "Bearer test-secret")
            body = json.loads(request.content)
            if body["method"] != "initialize":
                return httpx.Response(202)
            event = f"event: message\ndata: {json.dumps(initialize_response(request))}\n\n"
            return httpx.Response(200, text=event, headers={"content-type": "text/event-stream"})

        result = await self.run_request(
            respond, {"transport": "streamable_http", "headers": {"Authorization": "Bearer test-secret"}}
        )
        self.assertTrue(result["success"], result)

    async def test_legacy_sse_uses_endpoint_event_then_posts_initialize(self):
        stream = EventStream()
        stream.events.put_nowait(b"event: endpoint\ndata: /messages?session_id=test-session\n\n")
        requests = []

        def respond(request):
            requests.append(request)
            self.assertEqual(request.headers["authorization"], "Bearer test-secret")
            if request.method == "GET":
                return httpx.Response(200, stream=stream, headers={"content-type": "text/event-stream"})
            self.assertEqual(request.url.path, "/messages")
            body = json.loads(request.content)
            if body["method"] == "initialize":
                event = f"event: message\ndata: {json.dumps(initialize_response(request))}\n\n"
                stream.events.put_nowait(event.encode())
            return httpx.Response(202)

        result = await self.run_request(
            respond, {"transport": "sse", "type": "http", "headers": {"Authorization": "Bearer test-secret"}}
        )
        self.assertTrue(result["success"], result)
        self.assertEqual(requests[0].method, "GET")
        self.assertIn("POST", [request.method for request in requests])
        self.assertTrue(stream.closed)

    async def test_remote_http_errors_include_status_and_method_without_the_private_url(self):
        for status in (401, 403, 404, 405, 500):
            with self.subTest(status=status):
                result = await self.run_request(lambda _, status=status: httpx.Response(status))
                self.assertFalse(result["success"])
                self.assertIn(f"远端 MCP 返回 HTTP {status}（POST）", result["message"])
                self.assertNotIn("private-token", result["message"])

    async def test_legacy_sse_preserves_a_post_authentication_error(self):
        stream = EventStream()
        stream.events.put_nowait(b"event: endpoint\ndata: /messages\n\n")

        def respond(request):
            if request.method == "GET":
                return httpx.Response(200, stream=stream, headers={"content-type": "text/event-stream"})
            return httpx.Response(401)

        result = await self.run_request(respond, {"type": "sse", "timeout": 0.05})
        self.assertFalse(result["success"])
        self.assertIn("远端 MCP 返回 HTTP 401（POST）", result["message"])
        self.assertTrue(stream.closed)

    async def test_http_200_without_valid_mcp_initialization_is_rejected(self):
        for response in (
            httpx.Response(200, json={"status": "ok"}),
            httpx.Response(200, text="<html>Login</html>", headers={"content-type": "text/html"}),
        ):
            with self.subTest(content=response.headers["content-type"]):
                result = await self.run_request(lambda _, response=response: response)
                self.assertFalse(result["success"])

    async def test_json_rpc_error_is_not_a_successful_connection(self):
        def respond(request):
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "id": json.loads(request.content)["id"],
                    "error": {"code": -32603, "message": "MCP service unavailable"},
                },
            )

        result = await self.run_request(respond)
        self.assertFalse(result["success"])
        self.assertIn("MCP service unavailable", result["message"])

    async def test_timeout_and_network_failure_are_reported(self):
        async def slow(_):
            await asyncio.sleep(10)
            return httpx.Response(200)

        result = await self.run_request(slow, {"timeout": 0.05})
        self.assertFalse(result["success"])
        self.assertIn("握手超时", result["message"])

        def fail(_):
            raise httpx.ConnectError("unreachable")

        result = await self.run_request(fail)
        self.assertFalse(result["success"])
        self.assertIn("unreachable", result["message"])

    async def test_local_api_returns_200_with_remote_failure_in_the_result(self):
        app = FastAPI()
        app.include_router(settings.router, prefix="/api/settings")
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://local") as client:
            with patch.object(
                settings,
                "_check_mcp_connection",
                side_effect=httpx.HTTPStatusError(
                    "Method Not Allowed",
                    request=httpx.Request("POST", "https://mcp.example/mcp"),
                    response=httpx.Response(405),
                ),
            ):
                response = await client.post(
                    "/api/settings/mcp/test", json={"name": "test-mcp", "config": {"url": "https://mcp.example/mcp"}}
                )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["success"])
        self.assertIn("HTTP 405", response.json()["message"])

    async def test_invalid_deadline_is_rejected_before_connecting(self):
        with patch.object(settings, "_check_mcp_connection") as check:
            for timeout in (0, -1, "NaN", "Infinity"):
                with self.subTest(timeout=timeout):
                    result = await settings.test_mcp_server(
                        settings.MCPServerTestRequest(config={"url": "https://mcp.example/mcp", "timeout": timeout})
                    )
                    self.assertFalse(result["success"])
            check.assert_not_called()


if __name__ == "__main__":
    unittest.main()
