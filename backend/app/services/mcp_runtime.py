"""Shared MCP lifecycle state and an HTTP wrapper for the mounted SDK app.

The GUI imports this module to start/stop MCP and display recent clients. Keeping
it independent of FastMCP and the WPS bridge avoids initializing the server when
the GUI only needs its state.
"""

from __future__ import annotations

import json
import threading
import time
from typing import Any

ACTIVE_SECONDS = 120


class McpRuntime:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._enabled = False
        self._ready = False
        self._clients: dict[tuple[str, str], dict[str, Any]] = {}

    def set_ready(self, ready: bool) -> None:
        with self._lock:
            self._ready = ready
            if not ready:
                self._enabled = False
                self._clients.clear()

    def start(self) -> bool:
        with self._lock:
            if not self._ready:
                return False
            self._enabled = True
            return True

    def stop(self) -> None:
        with self._lock:
            self._enabled = False
            self._clients.clear()

    def enabled(self) -> bool:
        with self._lock:
            return self._enabled and self._ready

    def seen(self, host: str, user_agent: str, client_name: str | None = None) -> None:
        now = time.monotonic()
        key = (host, user_agent)
        with self._lock:
            if not (self._enabled and self._ready):
                return
            previous = self._clients.get(key, {})
            name = client_name or previous.get("name") or user_agent or "Unknown client"
            self._clients[key] = {"name": name[:100], "last_seen": now}

    def snapshot(self) -> dict[str, Any]:
        now = time.monotonic()
        with self._lock:
            self._clients = {
                key: value
                for key, value in self._clients.items()
                if now - value["last_seen"] < ACTIVE_SECONDS
            }
            clients = [
                {"name": value["name"], "seconds_ago": int(now - value["last_seen"])}
                for value in self._clients.values()
            ]
            clients.sort(key=lambda item: item["seconds_ago"])
            return {"ready": self._ready, "running": self._ready and self._enabled, "clients": clients}


runtime = McpRuntime()


class ControlledMcpApp:
    """Gate MCP requests and observe successful HTTP activity without changing the SDK."""

    def __init__(self, app: Any, state: McpRuntime = runtime) -> None:
        self.app = app
        self.state = state

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        if not self.state.enabled():
            body = b'{"error":"MCP server is stopped"}'
            await send({"type": "http.response.start", "status": 503, "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
            ]})
            await send({"type": "http.response.body", "body": body})
            return

        headers = dict(scope.get("headers", []))
        agent = headers.get(b"user-agent", b"").decode("utf-8", "replace")[:200]
        client = scope.get("client")
        host = client[0] if client else ""
        body_parts: list[bytes] = []
        body_length = 0

        async def observed_receive():
            nonlocal body_length
            message = await receive()
            if message["type"] == "http.request" and body_length <= 16384:
                part = message.get("body", b"")
                body_length += len(part)
                if body_length <= 16384:
                    body_parts.append(part)
                else:
                    body_parts.clear()
            return message

        async def observed_send(message):
            if (scope.get("method") == "POST" and message["type"] == "http.response.start"
                    and 200 <= message["status"] < 300):
                name = None
                if scope.get("method") == "POST" and body_parts:
                    try:
                        payload = json.loads(b"".join(body_parts))
                        if isinstance(payload, dict) and payload.get("method") == "initialize":
                            info = payload.get("params", {}).get("clientInfo", {})
                            if isinstance(info, dict) and isinstance(info.get("name"), str):
                                name = info["name"].strip() or None
                    except (ValueError, TypeError, AttributeError):
                        pass
                self.state.seen(host, agent, name)
            await send(message)

        await self.app(scope, observed_receive, observed_send)
