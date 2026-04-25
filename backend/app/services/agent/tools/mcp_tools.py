"""MCP 工具加载器 — 从用户设置中读取 MCP 服务器配置并加载为 LangChain 工具。"""

import asyncio
import concurrent.futures
import json
import os
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from app.core.config import get_user_settings_file


def _apply_proxy_to_environ() -> None:
    """将用户代理配置写入 os.environ，供 httpx / curl_cffi / 子进程使用。"""
    try:
        settings_path = get_user_settings_file()
        if settings_path and settings_path.exists():
            import json as _json

            data = _json.loads(settings_path.read_text(encoding="utf-8"))
        else:
            data = {}
    except Exception:
        data = {}

    proxy = data.get("proxy", {})
    enabled = proxy.get("enabled", False)
    host = str(proxy.get("host") or "").strip()
    port = proxy.get("port")

    if enabled and host and port:
        proxy_url = f"http://{host}:{port}"
        for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
            os.environ[key] = proxy_url
    else:
        # 未启用时清除代理环境变量
        for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
            os.environ.pop(key, None)


def _get_env_int(name: str, default: int) -> int:
    """Read positive integer from env with fallback."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(str(raw).strip())
        return value if value > 0 else default
    except Exception:
        return default


_MCP_PREVIEW_MAX_CHARS = _get_env_int("WORDAGENT_MCP_PREVIEW_MAX_CHARS", 100000)
_MCP_MODEL_MAX_CHARS = _get_env_int("WORDAGENT_MCP_MODEL_MAX_CHARS", 100000)


def _to_jsonable(value: Any) -> Any:
    """Best-effort convert objects to JSON-serializable values."""
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(v) for v in value]
    return str(value)


def _truncate_text(text: str, max_chars: int = 1200) -> tuple[str, bool]:
    """Truncate oversized text to keep UI/model payload bounded."""
    if not text:
        return "", False
    if max_chars <= 0 or len(text) <= max_chars:
        return text, False

    # 保留头部信息，末尾追加截断提示，避免上下文无限膨胀。
    keep = max(0, max_chars - 80)
    omitted = max(0, len(text) - keep)
    truncated = f"{text[:keep]}\n\n...[内容过长，已截断 {omitted} 个字符]"
    return truncated, True


_IMG_URL_LINE_PATTERN = re.compile(
    r"https?://[^\s\)]+\.(?:png|jpe?g|gif|svg|webp)(?:[?\#][^\s\)]*)?",
    re.IGNORECASE,
)
_IMG_EXT_PATTERN = re.compile(r"\.(?:png|jpe?g|gif|svg|webp|bmp|ico|tiff?)(?:$|[?\#])", re.IGNORECASE)
_RELATIVE_MD_IMAGE_PATTERN = re.compile(r"!\[[^\]]*\]\((?!https?://)([^)]+)\)", re.IGNORECASE)
_IMG_PATH_HINTS = ("/img/", "/image/", "/images/", "/photo/", "/photos/", "/afts/img/")
_IMAGE_URL_CACHE: dict[str, bool] = {}


def _is_image_url(url: str) -> bool:
    """Check whether a URL likely points to an image resource."""
    u = (url or "").strip()
    if not u:
        return False

    cached = _IMAGE_URL_CACHE.get(u)
    if cached is not None:
        return cached

    parsed = urlparse(u)
    if parsed.scheme not in {"http", "https"}:
        _IMAGE_URL_CACHE[u] = False
        return False

    path_lower = (parsed.path or "").lower()
    if _IMG_EXT_PATTERN.search(path_lower):
        _IMAGE_URL_CACHE[u] = True
        return True

    if any(hint in path_lower for hint in _IMG_PATH_HINTS):
        _IMAGE_URL_CACHE[u] = True
        return True

    # 对无后缀 URL 进行远端 Content-Type 探测
    is_img = _probe_image_content_type(u)
    _IMAGE_URL_CACHE[u] = is_img
    return is_img


def _probe_image_content_type(url: str) -> bool:
    """Probe remote URL headers/body to determine whether it's an image."""
    user_agent = "Mozilla/5.0"

    # 优先 HEAD，避免下载正文
    try:
        req = Request(url, headers={"User-Agent": user_agent}, method="HEAD")
        with urlopen(req, timeout=4) as resp:
            ctype = str(resp.headers.get("Content-Type", "")).lower()
            if ctype.startswith("image/"):
                return True
    except Exception:
        pass

    # 回退 GET + Range 仅读取极少字节
    try:
        req = Request(
            url,
            headers={
                "User-Agent": user_agent,
                "Range": "bytes=0-0",
            },
        )
        with urlopen(req, timeout=5) as resp:
            ctype = str(resp.headers.get("Content-Type", "")).lower()
            if ctype.startswith("image/"):
                return True
    except Exception:
        pass

    return False


def _extract_readable_text(value: Any) -> str | None:
    """Extract human-friendly text from common MCP payload shapes."""
    if isinstance(value, str):
        return value

    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            extracted = _extract_readable_text(item)
            if extracted:
                parts.append(extracted)
        return "\n".join(parts) if parts else None

    if isinstance(value, dict):
        # 常见文本字段优先
        for key in ("text", "content", "message", "summary"):
            v = value.get(key)
            if isinstance(v, str) and v.strip():
                return v

        # URL 字段单独处理（图片/资源链接）
        url = value.get("url")
        if isinstance(url, str) and url.strip():
            return url.strip()

        # 常见嵌套字段递归提取
        for key in ("output", "result", "data", "outputs", "items"):
            if key in value:
                extracted = _extract_readable_text(value.get(key))
                if extracted:
                    return extracted

    return None


def _strip_noise_lines(text: str) -> str:
    """Remove service metadata lines that are not user-facing content."""
    kept: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if re.match(r"(?i)^request\s*id\s*:", stripped):
            continue
        if re.match(r"(?i)^\*?note\s*:", stripped):
            continue
        kept.append(line)
    cleaned = "\n".join(kept)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _convert_image_url_lines_to_markdown(text: str) -> str:
    """Convert standalone image URL lines to Markdown image syntax for frontend rendering."""
    converted: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("http") and (" " not in stripped) and _is_image_url(stripped):
            converted.append(f"![MCP 图片]({stripped})")
        else:
            converted.append(line)
    return "\n".join(converted)


def _strip_relative_markdown_images(text: str) -> str:
    """Replace relative Markdown image links to avoid local 404 requests in frontend rendering."""

    def _repl(match: re.Match[str]) -> str:
        url = (match.group(1) or "").strip()
        return f"[图片链接已省略: {url}]" if url else "[图片链接已省略]"

    return _RELATIVE_MD_IMAGE_PATTERN.sub(_repl, text)


def _serialize_mcp_result_text(result: Any) -> str:
    """Serialize MCP result into readable text for preview/model context."""
    extracted = _extract_readable_text(result)
    if extracted:
        raw = _convert_image_url_lines_to_markdown(_strip_noise_lines(extracted))
    else:
        # 兜底：没有可读文本时再展示结构化 JSON
        try:
            raw = json.dumps(_to_jsonable(result), ensure_ascii=False, indent=2)
        except Exception:
            raw = str(result)

    return _strip_relative_markdown_images(raw)


def _build_result_preview(result: Any, max_chars: int = 1200) -> tuple[str, int, bool]:
    """Build readable preview text for arbitrary MCP result payload."""
    raw = _serialize_mcp_result_text(result)

    preview, truncated = _truncate_text(raw, max_chars=max_chars)
    return preview, len(raw), truncated


def _build_result_for_model(result: Any, max_chars: int = 12000) -> str:
    """Build compact MCP output text injected back to the model as tool result."""
    raw = _serialize_mcp_result_text(result)
    compact, _ = _truncate_text(raw, max_chars=max_chars)
    return compact


def _emit_stream_event(event: dict[str, Any]) -> None:
    """Emit stream event if running inside a LangGraph tool context."""
    try:
        from langgraph.config import get_stream_writer

        writer = get_stream_writer()
        if writer:
            writer(event)
    except Exception:
        # 非流式上下文或获取 writer 失败时静默忽略
        pass


def _format_mcp_exception(exc: Exception) -> str:
    """Format exceptions (including ExceptionGroup) into a compact readable message."""
    base = str(exc).strip() or exc.__class__.__name__
    sub_errors = getattr(exc, "exceptions", None)
    if isinstance(sub_errors, (list, tuple)) and sub_errors:
        first = sub_errors[0]
        first_text = str(first).strip() or first.__class__.__name__
        return f"{base}; first sub-error: {first_text}"
    return base


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
            if isinstance(config.get("args"), list):
                entry["args"] = config["args"]
            print(f"[MCP] 🔧 {name}: command={command} args={entry.get('args')}")

            entry["transport"] = transport or "stdio"

            # 构建 env：从系统环境变量开始，叠加用户自定义 env 和 Python 目录
            # 必须继承完整的 os.environ，否则子进程缺少 TEMP/SYSTEMROOT 等关键变量
            merged_env = dict(os.environ)
            user_env = config.get("env") if isinstance(config.get("env"), dict) else {}
            if user_env:
                merged_env.update({str(k): str(v) for k, v in user_env.items()})
            python_dir = str(Path(sys.executable).parent)
            if python_dir not in merged_env.get("PATH", "").split(os.pathsep):
                merged_env["PATH"] = python_dir + os.pathsep + merged_env.get("PATH", "")
            entry["env"] = merged_env
        else:
            continue

        client_config[name] = entry

    return client_config


def _wrap_mcp_tool_for_sync(tool, loop: asyncio.AbstractEventLoop, call_timeout_seconds: int = 90):
    """将异步 MCP 工具包装为同步可调用，通过主事件循环分派执行。"""
    from langchain_core.tools import StructuredTool

    def sync_fn(**kwargs):
        import time as _time

        print(f"[MCP] ▶ 调用 {tool.name}，参数: {list(kwargs.keys())}")
        _emit_stream_event(
            {
                "type": "mcp_tool_call",
                "toolName": tool.name,
                "args": _to_jsonable(kwargs),
                "content": f"调用 MCP 工具: {tool.name}",
            }
        )
        t0 = _time.time()
        future = asyncio.run_coroutine_threadsafe(tool.ainvoke(kwargs), loop)
        try:
            result = future.result(timeout=call_timeout_seconds)
            preview, output_len, truncated = _build_result_preview(result, max_chars=_MCP_PREVIEW_MAX_CHARS)
            model_output = _build_result_for_model(result, max_chars=_MCP_MODEL_MAX_CHARS)
            _emit_stream_event(
                {
                    "type": "mcp_tool_result",
                    "toolName": tool.name,
                    "outputPreview": preview,
                    "outputLength": output_len,
                    "truncated": truncated,
                    "isError": False,
                    "content": f"MCP 工具 {tool.name} 已返回结果",
                }
            )
            print(f"[MCP] ✅ {tool.name} 完成，耗时 {_time.time() - t0:.1f}s")
            return model_output
        except concurrent.futures.TimeoutError:
            future.cancel()
            timeout_msg = f"MCP tool {tool.name} timed out after {call_timeout_seconds}s"
            _emit_stream_event(
                {
                    "type": "mcp_tool_result",
                    "toolName": tool.name,
                    "outputPreview": f"工具执行超时: {timeout_msg}",
                    "outputLength": 0,
                    "truncated": False,
                    "isError": True,
                    "content": f"MCP 工具 {tool.name} 执行超时",
                }
            )
            print(f"[MCP] ❌ {tool.name} 超时，耗时 {_time.time() - t0:.1f}s")
            raise TimeoutError(timeout_msg)
        except Exception as e:
            err_text = _format_mcp_exception(e)
            _emit_stream_event(
                {
                    "type": "mcp_tool_result",
                    "toolName": tool.name,
                    "outputPreview": f"工具执行失败: {err_text}",
                    "outputLength": 0,
                    "truncated": False,
                    "isError": True,
                    "content": f"MCP 工具 {tool.name} 执行失败",
                }
            )
            print(f"[MCP] ❌ {tool.name} 失败，耗时 {_time.time() - t0:.1f}s，错误: {err_text}")
            raise

    return StructuredTool(
        name=tool.name,
        description=tool.description,
        func=sync_fn,
        args_schema=tool.args_schema,
    )


async def load_mcp_tools() -> tuple[list, list, list[dict[str, str]]]:
    """
    异步加载所有已配置的 MCP 服务器工具，每个服务器独立加载互不影响。

    返回的工具已包装为同步可调用，可在线程中通过 tool.invoke() 使用。
    返回值: (tools, clients, failed_servers) — clients 列表需在使用期间保持存活。
    failed_servers: [{"name": str, "error": str}]，用于前端状态展示。
    """
    # 根据用户配置设置代理环境变量，确保 MCP HTTP 请求也走代理
    _apply_proxy_to_environ()

    config = _load_mcp_server_configs()
    if not config:
        print("[MCP] ℹ️ 未配置 MCP 服务器，跳过加载")
        return [], [], []

    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient
    except ImportError:
        print("[MCP] ⚠️ langchain-mcp-adapters 未安装，跳过 MCP 工具加载")
        return [], [], [{"name": "MCP", "error": "缺少依赖 langchain-mcp-adapters"}]

    loop = asyncio.get_running_loop()
    all_tools: list = []
    live_clients: list = []
    failed_servers: list[dict[str, str]] = []

    for name, server_cfg in config.items():
        try:
            client = MultiServerMCPClient({name: server_cfg})
            raw_tools = await client.get_tools()
            wrapped = [_wrap_mcp_tool_for_sync(t, loop) for t in raw_tools]
            all_tools.extend(wrapped)
            live_clients.append(client)
            print(f"[MCP] ✅ {name}: 已加载 {len(wrapped)} 个工具 {[t.name for t in wrapped]}")
        except Exception as e1:
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
                    failed_servers.append({"name": name, "error": str(e2)})
            else:
                import traceback

                print(f"[MCP] ❌ {name}: 加载失败")
                traceback.print_exc()
                failed_servers.append({"name": name, "error": str(e1)})

    if all_tools:
        print(f"[MCP] 📊 共加载 {len(all_tools)} 个工具 (来自 {len(live_clients)} 个服务器)")
    else:
        print("[MCP] ⚠️ 所有 MCP 服务器均加载失败，无可用工具")

    return all_tools, live_clients, failed_servers


def build_mcp_tools_prompt(mcp_tools: list) -> str:
    """Build system prompt text for available MCP tools."""
    if not mcp_tools:
        return ""

    lines = [
        "## External MCP Tools",
        "",
        "In addition to document tools, you can use these extra tools provided by MCP servers:",
        "",
    ]
    for t in mcp_tools:
        desc = t.description or "No description"
        # Use first line only
        first_line = desc.split("\n")[0].strip()
        lines.append(f"- `{t.name}`: {first_line}")

    lines.extend(
        [
            "",
            "When user requests require external information (web search, retrieval, data query), proactively call these MCP tools.",
            "Invocation pattern is the same as for built-in tools.",
        ]
    )

    return "\n".join(lines)
