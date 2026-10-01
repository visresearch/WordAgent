"""Define shared FastMCP tools for WPS and Microsoft Word add-in pages.

Availability and client activity are owned by mcp_runtime so the GUI can control
the mounted endpoint without importing or initializing this module itself.
"""

from __future__ import annotations

import asyncio
import ipaddress
import uuid
from typing import Literal
from urllib.parse import urlparse

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from mcp.server.fastmcp import FastMCP

from app.services.mcp_runtime import ControlledMcpApp
from app.services.tools.schemas import DocumentOutput, DocumentQuery, Run

Host = Literal["wps", "word"]


class DocumentBridge:
    def __init__(self, host: Host) -> None:
        self.host = host
        self.label = "Microsoft Word" if host == "word" else "WPS"
        self.socket: WebSocket | None = None
        self.pending: dict[str, asyncio.Future[dict]] = {}
        self.send_lock = asyncio.Lock()

    async def connect(self, socket: WebSocket) -> None:
        self.socket = socket
        try:
            await socket.accept()
            while True:
                response = await socket.receive_json()
                if not isinstance(response, dict):
                    continue
                request_id = response.get("requestId")
                if not isinstance(request_id, str):
                    continue
                future = self.pending.get(request_id)
                if future is not None and not future.done() and self.socket is socket:
                    future.set_result(response)
        except WebSocketDisconnect:
            pass
        finally:
            self.disconnect(socket)

    def disconnect(self, socket: WebSocket) -> None:
        if self.socket is not socket:
            return
        self.socket = None
        for future in self.pending.values():
            if not future.done():
                future.set_exception(RuntimeError(f"{self.label} 插件页面已断开连接"))

    async def call(self, tool: str, arguments: dict) -> dict:
        socket = self.socket
        if socket is None:
            raise RuntimeError(f"{self.label} 插件页面未连接；请打开加载项侧栏")
        request_id = str(uuid.uuid4())
        future: asyncio.Future[dict] = asyncio.get_running_loop().create_future()
        self.pending[request_id] = future
        try:
            async with self.send_lock:
                if self.socket is not socket:
                    raise RuntimeError(f"{self.label} 插件页面已断开连接")
                await socket.send_json({"requestId": request_id, "tool": tool, "arguments": arguments})
            try:
                response = await asyncio.wait_for(future, timeout=120)
            except TimeoutError as exc:
                raise RuntimeError(f"{self.label} 工具调用超时；请检查加载项侧栏") from exc
            if response.get("error"):
                raise RuntimeError(str(response["error"]))
            result = response.get("result")
            if not isinstance(result, dict):
                raise RuntimeError(f"{self.label} 返回了无效的工具结果")
            return result
        finally:
            self.pending.pop(request_id, None)


class BridgeRegistry:
    def __init__(self) -> None:
        self.connections: dict[Host, set[DocumentBridge]] = {"wps": set(), "word": set()}

    async def connect(self, socket: WebSocket, host: Host) -> None:
        connection = DocumentBridge(host)
        self.connections[host].add(connection)
        try:
            await connection.connect(socket)
        finally:
            self.connections[host].discard(connection)

    async def call(self, tool: str, arguments: dict) -> dict:
        arguments = dict(arguments)
        host = arguments.pop("host", None)
        if host is None:
            active_hosts = [name for name, connections in self.connections.items() if connections]
            if not active_hosts:
                raise RuntimeError("WPS 插件页面未连接，Microsoft Word 插件页面也未连接；请打开加载项侧栏")
            if len(active_hosts) > 1:
                raise RuntimeError('WPS 和 Microsoft Word 均已连接；请指定 host="wps" 或 host="word"')
            host = active_hosts[0]
        connections = self.connections[host]
        if not connections:
            label = "Microsoft Word" if host == "word" else "WPS"
            raise RuntimeError(f"{label} 插件页面未连接；请打开加载项侧栏")
        if len(connections) > 1:
            raise RuntimeError(f"{host} 有多个加载项侧栏连接；请仅保留目标文档的侧栏后再调用")
        return await next(iter(connections)).call(tool, arguments)


bridge = BridgeRegistry()
router = APIRouter()


def _local_websocket(socket: WebSocket) -> bool:
    host = socket.client.host if socket.client else ""
    try:
        if not ipaddress.ip_address(host).is_loopback:
            return False
    except ValueError:
        return False
    origin = socket.headers.get("origin")
    if not origin:
        return True
    parsed = urlparse(origin)
    return parsed.scheme in {"http", "https"} and parsed.hostname in {"localhost", "127.0.0.1", "::1"}


@router.websocket("/mcp/bridge")
async def document_mcp_bridge(socket: WebSocket) -> None:
    if not _local_websocket(socket):
        await socket.close(code=1008)
        return
    # Legacy WPS pages omit host; Word identifies itself on the same URL.
    host = socket.query_params.get("host", "wps")
    if host not in {"wps", "word"}:
        await socket.close(code=1008)
        return
    await bridge.connect(socket, host)


mcp = FastMCP(
    "WordAgent",
    instructions=(
        "Operate documents through the connected WPS or Microsoft Word add-in using the same tools. "
        "host='word' targets Microsoft Word; host='wps' targets WPS. Omit host only when one host is connected. "
        "For Microsoft Word, docId must be 0 and refers to the document owning the connected task pane, "
        "not necessarily the foreground window. Keep only the target Word document's task pane open. "
        "For WPS, docId=0 means the active document; a nonzero docId selects an open document. "
        "Read or search before editing to obtain current paraIDs. Re-read after changes. "
        "After create_document in Microsoft Word, close the old task pane and open the add-in in the new document "
        "before subsequent calls."
    ),
    streamable_http_path="/",
    stateless_http=True,
    json_response=True,
)
mcp_app = ControlledMcpApp(mcp.streamable_http_app())


@mcp.tool()
async def read_document(
    startParaIndex: int = 0,
    endParaIndex: int = -1,
    startParaID: int | None = None,
    endParaID: int | None = None,
    docId: int = 0,
    mode: Literal["full", "lightweight"] = "full",
    host: Host | None = None,
) -> dict:
    """Read a paragraph range (0-based indices or paraIDs); endParaIndex=-1 reads to the end."""
    return await bridge.call("read_document", locals())


@mcp.tool()
async def search_document(query: DocumentQuery, docId: int = 0, host: Host | None = None) -> dict:
    """Search the document with the same style query DSL used by WordAgent."""
    return await bridge.call(
        "search_document", {"query": query.model_dump(exclude_none=True), "docId": docId, "host": host}
    )


@mcp.tool()
async def delete_document(paraIDs: list[int], docId: int = 0, host: Host | None = None) -> dict:
    """Delete paragraphs by their current paraIDs. Read first to identify the IDs."""
    return await bridge.call("delete_document", {"paraIDs": paraIDs, "docId": docId, "host": host})


@mcp.tool()
async def edit_document(
    paraID: int,
    runs: list[Run],
    docId: int = 0,
    host: Host | None = None,
    styles: dict[str, list] | None = None,
) -> dict:
    """Replace a paragraph, preserving its paragraph style. For runs with rStyle IDs, supply the styles dictionary from a full read; omit rStyle to preserve character formatting."""
    resolved_runs = []
    for run in runs:
        value = run.model_dump(exclude_none=True)
        if run.rStyle is not None:
            style = (styles or {}).get(run.rStyle)
            if not isinstance(style, list) or len(style) != 11:
                raise ValueError(f"字符样式 {run.rStyle} 未解析；请传入完整读取返回的 styles 字典，或省略 rStyle")
            value["rStyle"] = style
        resolved_runs.append(value)
    return await bridge.call("edit_document", {"paraID": paraID, "runs": resolved_runs, "docId": docId, "host": host})


@mcp.tool()
async def create_document(host: Host | None = None) -> dict:
    """Create and open a blank DOCX. In Word, reconnect the add-in in the new document before editing it."""
    return await bridge.call("create_document", {"host": host})


@mcp.tool()
async def insert_break(
    paraID: int,
    breakType: Literal["wdLineBreak", "wdPageBreak", "wdSectionBreakNextPage"],
    docId: int = 0,
    host: Host | None = None,
) -> dict:
    """Insert a line break, page break or next-page section break after a paragraph."""
    return await bridge.call("insert_break", locals())


@mcp.tool()
async def generate_document(
    document: DocumentOutput,
    insertParaID: int = 0,
    docId: int = 0,
    host: Host | None = None,
) -> dict:
    """Insert styled document blocks after insertParaID (0 inserts at the start)."""
    return await bridge.call(
        "generate_document",
        {
            "document": document.model_dump(exclude_none=True),
            "insertParaID": insertParaID,
            "docId": docId,
            "host": host,
        },
    )
