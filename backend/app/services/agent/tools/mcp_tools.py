"""MCP 工具加载器 — 从用户设置中读取 MCP 服务器配置并加载为 LangChain 工具。"""

import asyncio
import json
from typing import Any

from app.core.config import get_user_settings_file


def _load_mcp_server_configs() -> dict[str, dict[str, Any]]:
    """从 user_settings.json 读取 MCP 服务器配置，转为 MultiServerMCPClient 格式。"""
    settings_file = get_user_settings_file()
    if not settings_file.exists():
        return {}

    try:
        data = json.loads(settings_file.read_text(encoding="utf-8"))
    except Exception:
        return {}

    mcp_servers = data.get("mcpServers", [])
    if not isinstance(mcp_servers, list):
        return {}

    client_config: dict[str, dict[str, Any]] = {}
    for server in mcp_servers:
        name = server.get("name", "").strip()
        config = server.get("config", {})
        if not name or not isinstance(config, dict):
            continue

        entry: dict[str, Any] = {}

        url = str(config.get("url") or config.get("endpoint") or "").strip()
        command = str(config.get("command") or "").strip()
        # 用户配置可能使用 "type" 或 "transport"
        transport = str(config.get("transport") or config.get("type") or "").strip()
        # 统一 transport 值（langchain-mcp-adapters 使用 "http" 表示 streamable HTTP）
        if transport in ("streamable_http", "streamable-http"):
            transport = "http"

        if url:
            entry["url"] = url
            # URL 类型的 MCP 服务器默认使用 streamable HTTP（兼容大多数现代 MCP 服务器）
            entry["transport"] = transport if transport in ("sse", "http") else "http"
            if isinstance(config.get("headers"), dict):
                entry["headers"] = config["headers"]
        elif command:
            entry["command"] = command
            entry["transport"] = transport or "stdio"
            if isinstance(config.get("args"), list):
                entry["args"] = config["args"]
            if isinstance(config.get("env"), dict):
                entry["env"] = config["env"]
        else:
            continue

        client_config[name] = entry

    return client_config


def _wrap_mcp_tool_for_sync(tool, loop: asyncio.AbstractEventLoop):
    """将异步 MCP 工具包装为同步可调用，通过主事件循环分派执行。"""
    from langchain_core.tools import StructuredTool

    def sync_fn(**kwargs):
        future = asyncio.run_coroutine_threadsafe(tool.ainvoke(kwargs), loop)
        return future.result(timeout=300)

    return StructuredTool(
        name=tool.name,
        description=tool.description,
        func=sync_fn,
        args_schema=tool.args_schema,
    )


async def load_mcp_tools() -> tuple[list, Any | None]:
    """
    异步加载所有已配置的 MCP 服务器工具。

    返回的工具已包装为同步可调用，可在线程中通过 tool.invoke() 使用。
    返回值: (tools, client) — client 需在使用期间保持存活。
    """
    config = _load_mcp_server_configs()
    if not config:
        print("[MCP] ℹ️ 未配置 MCP 服务器，跳过加载")
        return [], None

    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient
    except ImportError:
        print("[MCP] ⚠️ langchain-mcp-adapters 未安装，跳过 MCP 工具加载")
        return [], None

    try:
        loop = asyncio.get_running_loop()
        client = MultiServerMCPClient(config)
        raw_tools = await client.get_tools()
        wrapped = [_wrap_mcp_tool_for_sync(t, loop) for t in raw_tools]
        print(f"[MCP] ✅ 已加载 {len(wrapped)} 个 MCP 工具: {[t.name for t in wrapped]}")
        return wrapped, client
    except Exception as e:
        # SSE 连接失败时，尝试将 sse 的 transport 改为 streamable_http 重试
        sse_servers = [name for name, cfg in config.items() if cfg.get("transport") == "sse"]
        if sse_servers:
            print(f"[MCP] ⚠️ SSE 连接失败，尝试以 streamable_http 重试: {sse_servers}")
            for name in sse_servers:
                config[name]["transport"] = "streamable_http"
            try:
                client = MultiServerMCPClient(config)
                raw_tools = await client.get_tools()
                wrapped = [_wrap_mcp_tool_for_sync(t, loop) for t in raw_tools]
                print(f"[MCP] ✅ 已加载 {len(wrapped)} 个 MCP 工具 (streamable_http 回退): {[t.name for t in wrapped]}")
                return wrapped, client
            except Exception as e2:
                print(f"[MCP] ❌ 加载 MCP 工具失败 (含回退): {e2}")
        else:
            print(f"[MCP] ❌ 加载 MCP 工具失败: {e}")
        import traceback
        traceback.print_exc()
        return [], None


def build_mcp_tools_prompt(mcp_tools: list) -> str:
    """构建 MCP 工具的系统提示，让模型知道有哪些额外工具可用。"""
    if not mcp_tools:
        return ""

    lines = [
        "## 外部 MCP 工具",
        "",
        "除了文档操作工具外，你还可以使用以下由 MCP 服务器提供的额外工具：",
        "",
    ]
    for t in mcp_tools:
        desc = t.description or "无描述"
        # 截取首行描述
        first_line = desc.split("\n")[0].strip()
        lines.append(f"- `{t.name}`: {first_line}")

    lines.extend([
        "",
        "当用户的请求涉及网络搜索、信息检索、数据查询等需要外部信息的场景时，"
        "应主动调用这些 MCP 工具来获取信息。",
        "调用这些工具与调用其他内置工具的方式完全相同。",
    ])

    return "\n".join(lines)
