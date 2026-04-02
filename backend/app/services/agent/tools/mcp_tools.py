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
        enabled = server.get("enabled", True)
        if isinstance(enabled, str):
            enabled = enabled.strip().lower() not in {"0", "false", "off", "no"}
        if not enabled:
            continue
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


async def load_mcp_tools() -> tuple[list, list]:
    """
    异步加载所有已配置的 MCP 服务器工具，每个服务器独立加载互不影响。

    返回的工具已包装为同步可调用，可在线程中通过 tool.invoke() 使用。
    返回值: (tools, clients) — clients 列表需在使用期间保持存活。
    """
    config = _load_mcp_server_configs()
    if not config:
        print("[MCP] ℹ️ 未配置 MCP 服务器，跳过加载")
        return [], []

    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient
    except ImportError:
        print("[MCP] ⚠️ langchain-mcp-adapters 未安装，跳过 MCP 工具加载")
        return [], []

    loop = asyncio.get_running_loop()
    all_tools: list = []
    live_clients: list = []

    for name, server_cfg in config.items():
        try:
            client = MultiServerMCPClient({name: server_cfg})
            raw_tools = await client.get_tools()
            wrapped = [_wrap_mcp_tool_for_sync(t, loop) for t in raw_tools]
            all_tools.extend(wrapped)
            live_clients.append(client)
            print(f"[MCP] ✅ {name}: 已加载 {len(wrapped)} 个工具 {[t.name for t in wrapped]}")
        except Exception:
            # SSE 连接失败时，尝试以 streamable_http 重试
            if server_cfg.get("transport") == "sse":
                try:
                    fallback_cfg = {**server_cfg, "transport": "streamable_http"}
                    client = MultiServerMCPClient({name: fallback_cfg})
                    raw_tools = await client.get_tools()
                    wrapped = [_wrap_mcp_tool_for_sync(t, loop) for t in raw_tools]
                    all_tools.extend(wrapped)
                    live_clients.append(client)
                    print(f"[MCP] ✅ {name}: 已加载 {len(wrapped)} 个工具 (streamable_http 回退)")
                    continue
                except Exception as e2:
                    print(f"[MCP] ❌ {name}: 加载失败 (含 streamable_http 回退): {e2}")
            else:
                import traceback

                print(f"[MCP] ❌ {name}: 加载失败")
                traceback.print_exc()

    if all_tools:
        print(f"[MCP] 📊 共加载 {len(all_tools)} 个工具 (来自 {len(live_clients)} 个服务器)")
    else:
        print("[MCP] ⚠️ 所有 MCP 服务器均加载失败，无可用工具")

    return all_tools, live_clients


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

    lines.extend(
        [
            "",
            "当用户的请求涉及网络搜索、信息检索、数据查询等需要外部信息的场景时，应主动调用这些 MCP 工具来获取信息。",
            "调用这些工具与调用其他内置工具的方式完全相同。",
        ]
    )

    return "\n".join(lines)
