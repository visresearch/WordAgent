"""
设置管理接口
保存和加载用户的大模型配置
"""

import asyncio
import json
import math
import os
import shutil
import tempfile
from contextlib import AsyncExitStack
from datetime import timedelta
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamable_http_client
from pydantic import BaseModel, Field

from app.core.config import get_temp_dir, get_upload_dir, get_user_settings_file
from app.core.logging import get_logger
from app.models.model_config import ModelConfig, ModelParameters
from app.services.memory import _get_memory_file, read_long_term_memory
from app.services.model_settings import (
    enrich_providers,
    load_model_parameters,
    normalize_legacy_parameters,
    provider_key,
    save_model_parameters,
)

logger = get_logger(__name__)
router = APIRouter()

# 设置文件路径
SETTINGS_FILE = get_user_settings_file()


def _clamp_temperature(value: Any) -> float:
    try:
        return min(1, max(0, float(value)))
    except (TypeError, ValueError):
        return 0.5


class ProviderConfig(BaseModel):
    """提供商配置"""

    name: str
    baseUrl: str
    apiKey: str
    apiType: str = "openai"  # openai / anthropic
    models: list[ModelConfig] = Field(default_factory=list)
    enabled: bool = True


class ProxyConfig(BaseModel):
    """代理配置"""

    enabled: bool = False
    host: str = "127.0.0.1"  # 代理 IP，如 127.0.0.1
    port: int = 7897  # 代理端口，如 7897


class UserSettings(BaseModel):
    """用户设置"""

    providers: list[ProviderConfig] = []
    # 基础设置
    showPanelOnStart: bool = True
    language: str = "zh-CN"
    # 代理设置
    proxy: ProxyConfig = ProxyConfig()
    # 个性化设置
    customPrompt: str = ""
    temperature: float = Field(default=0.5, ge=0, le=1)
    enableLongTermMemory: bool = False
    # MCP 服务器设置
    mcpServers: list[dict[str, Any]] = []


class MCPServerTestRequest(BaseModel):
    """MCP 服务器连接测试请求"""

    name: str = ""
    config: dict[str, Any] | str


@router.get("")
async def get_settings():
    """获取用户设置"""
    try:
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                data["temperature"] = _clamp_temperature(data.get("temperature", 0.5))
                stored = await asyncio.to_thread(load_model_parameters)
                data["providers"] = enrich_providers(data.get("providers", []), stored, data["temperature"])
                return UserSettings(**data)
        # 返回默认设置
        return UserSettings()
    except Exception as e:
        logger.error(f"读取设置失败: {e}")
        return UserSettings()


@router.post("")
async def save_settings(settings: UserSettings):
    """保存用户设置"""
    try:
        # 确保配置目录存在
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)

        # 读取现有设置，合并更新（保留未传入的字段）
        existing_data = {}
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                existing_data = json.load(f)

        # 合并：只用实际传入的字段覆盖，未传入的保留原值
        updates = settings.model_dump(exclude_unset=True)
        merged = {**existing_data, **updates}
        merged.pop("proofreadMode", None)
        merged["temperature"] = _clamp_temperature(merged.get("temperature", 0.5))

        stored = await asyncio.to_thread(load_model_parameters)
        previous = enrich_providers(existing_data.get("providers", []), stored, merged["temperature"])
        previous_parameters = {
            (provider_key(provider["name"]), model["id"]): model["parameters"]
            for provider in previous
            for model in provider.get("models", [])
        }
        for provider in merged.get("providers", []):
            for model in provider.get("models", []):
                old = previous_parameters.get((provider_key(provider["name"]), model["id"]), {})
                # Only explicit provider updates may override authoritative database values.
                changed_parameters = model.get("parameters") if "providers" in updates else {}
                parameters = {**old, **(changed_parameters or {})}
                model["parameters"] = ModelParameters.model_validate(
                    normalize_legacy_parameters(parameters, merged["temperature"])
                ).model_dump()

        # Persist model parameters in SQLite, retaining JSON compatibility for other settings consumers.
        await asyncio.to_thread(
            save_model_parameters, merged.get("providers", []), lambda: _write_settings_file(merged)
        )

        # 清除 LLM 客户端缓存，使代理等配置变更生效
        try:
            from app.services.llm_client import LLMClientManager

            LLMClientManager.clear_cache()
        except Exception:
            pass

        return {"message": "设置保存成功"}
    except Exception as e:
        logger.error(f"保存设置失败: {e}")
        raise HTTPException(status_code=500, detail=f"保存设置失败: {str(e)}")


def _write_settings_file(data: dict) -> None:
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=SETTINGS_FILE.parent, delete=False) as file:
            temporary_path = Path(file.name)
            json.dump(data, file, ensure_ascii=False, indent=2)
        os.replace(temporary_path, SETTINGS_FILE)
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()


async def _check_mcp_connection(url: str, transport: str, headers: dict, timeout: float) -> None:
    """通过 MCP 初始化握手测试远程连接，并在超时内关闭会话。"""
    post_error = None

    async def check_post_status(response: httpx.Response) -> None:
        nonlocal post_error
        # 保留 POST 的 HTTP 错误；Streamable HTTP 允许 GET/DELETE 返回 405。
        if response.request.method == "POST":
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as error:
                post_error = error
                raise

    def create_http_client(**kwargs) -> httpx.AsyncClient:
        return httpx.AsyncClient(follow_redirects=True, event_hooks={"response": [check_post_status]}, **kwargs)

    # 总超时也覆盖持续发送事件、但没有完成握手的 SSE 连接。
    try:
        async with asyncio.timeout(timeout):
            async with AsyncExitStack() as stack:
                if transport == "sse":
                    connection = sse_client(
                        url,
                        headers=headers,
                        timeout=timeout,
                        sse_read_timeout=timeout,
                        httpx_client_factory=create_http_client,
                    )
                else:
                    client = await stack.enter_async_context(create_http_client(headers=headers, timeout=timeout))
                    connection = streamable_http_client(url, http_client=client)
                streams = await stack.enter_async_context(connection)
                session = await stack.enter_async_context(
                    ClientSession(streams[0], streams[1], read_timeout_seconds=timedelta(seconds=timeout))
                )
                await session.initialize()
    except Exception:
        # 旧版 SSE 的写入任务可能吞掉 POST 错误，握手失败时返回原始状态码。
        if post_error is not None:
            raise post_error from None
        raise


def _format_mcp_connection_error(error: Exception, timeout: float) -> str:
    """提取 SDK 任务组中的具体错误，HTTP 错误不包含服务 URL。"""
    errors = [error]
    leaves = []
    while errors:
        current = errors.pop(0)
        nested = getattr(current, "exceptions", None)
        if isinstance(nested, list | tuple) and nested:
            errors.extend(nested)
        else:
            leaves.append(current)

    for current in leaves:
        if isinstance(current, httpx.HTTPStatusError):
            status = current.response.status_code
            hint = {
                401: "请检查鉴权信息",
                403: "请检查访问权限",
                404: "地址不存在，请检查 URL 路径",
                405: "请求方法不被支持，请检查传输类型和 URL",
            }.get(status)
            detail = f"远端 MCP 返回 HTTP {status}（{current.request.method}）"
            return f"{detail}：{hint}" if hint else detail
    if any(isinstance(current, TimeoutError | httpx.TimeoutException) for current in leaves):
        return f"MCP 握手超时（{timeout:g} 秒）"
    return str(leaves[0]).strip() or type(leaves[0]).__name__


@router.post("/mcp/test")
async def test_mcp_server(payload: MCPServerTestRequest):
    """测试 MCP 服务器连接"""
    try:
        config = payload.config
        if isinstance(config, str):
            try:
                config = json.loads(config)
            except Exception:
                return {"success": False, "message": "服务器配置不是合法 JSON"}

        if not isinstance(config, dict):
            return {"success": False, "message": "服务器配置必须是 JSON 对象"}

        server_name = payload.name.strip() or str(config.get("name", "")).strip() or "未命名服务器"

        # 优先按 URL 方式测试（SSE/HTTP MCP）
        url = str(config.get("url") or config.get("endpoint") or "").strip()
        if url:
            timeout = float(config.get("timeout", 8))
            if not math.isfinite(timeout) or timeout <= 0:
                return {"success": False, "message": "连接超时必须是大于 0 的有限秒数"}
            headers = config.get("headers") if isinstance(config.get("headers"), dict) else {}
            configured_transport = str(config.get("transport") or config.get("type") or "").strip()
            # Match the runtime loader: URL connections default to Streamable HTTP.
            transport = "sse" if configured_transport == "sse" else "http"

            try:
                await _check_mcp_connection(url, transport, headers, timeout)
                logger.info("[MCP 测试] %s (%s): MCP 握手成功", server_name, transport)
                return {
                    "success": True,
                    "message": f"{server_name} 连接成功（MCP 握手成功）",
                }
            except Exception as e:
                detail = _format_mcp_connection_error(e, timeout)
                logger.warning("[MCP 测试] %s (%s): %s", server_name, transport, detail)
                return {
                    "success": False,
                    "message": f"{server_name} 连接失败: {detail}",
                }

        # 其次按 stdio 方式测试（仅检查命令可执行，不真正启动进程）
        command = str(config.get("command") or "").strip()
        if command:
            if os.path.isabs(command):
                cmd_path = Path(command)
                if cmd_path.exists() and os.access(cmd_path, os.X_OK):
                    return {
                        "success": True,
                        "message": f"{server_name} 命令可用: {command}",
                    }
                return {
                    "success": False,
                    "message": f"{server_name} 命令不可执行: {command}",
                }

            resolved = shutil.which(command)
            if resolved:
                return {
                    "success": True,
                    "message": f"{server_name} 命令可用: {resolved}",
                }
            return {
                "success": False,
                "message": f"{server_name} 命令未找到: {command}",
            }

        return {
            "success": False,
            "message": "配置缺少 url 或 command 字段，无法测试连接",
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"测试连接失败: {str(e)}",
        }


@router.get("/wence-temp-dir")
async def get_wence_temp_dir():
    """获取用于前端图片导出的临时目录（wence_data/project/temp）。"""
    try:
        temp_dir = get_temp_dir()
        return {"dir": str(temp_dir)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取临时目录失败: {str(e)}")


# ============== 图片缓存管理 ==============


def _get_cache_dirs() -> list[Path]:
    """获取缓存目录（固定为 wence_data/project/temp + uploads）。"""
    return [get_temp_dir(), get_upload_dir()]


def _iter_cache_files(cache_dirs: list[Path]) -> list[Path]:
    """递归收集缓存目录下所有文件。"""
    files: list[Path] = []
    for cache_dir in cache_dirs:
        if not cache_dir.exists():
            continue
        files.extend([p for p in cache_dir.rglob("*") if p.is_file()])
    return files


@router.get("/cache/scan")
async def scan_cache():
    """扫描 wence_data/project/temp 与 uploads 缓存"""
    cache_dirs = _get_cache_dirs()

    count = 0
    total_size = 0
    for f in _iter_cache_files(cache_dirs):
        try:
            count += 1
            total_size += f.stat().st_size
        except Exception as e:
            logger.error(f"读取缓存文件大小失败 {f}: {e}")

    dirs_str = "；".join(str(d) for d in cache_dirs)
    return {
        "dir": dirs_str,
        "dirs": [str(d) for d in cache_dirs],
        "fileCount": count,
        "totalSize": total_size,
    }


@router.delete("/cache/clear")
async def clear_cache():
    """清除 wence_data/project/temp 与 uploads 缓存文件"""
    cache_dirs = _get_cache_dirs()
    existing_dirs = [d for d in cache_dirs if d.exists()]
    if not existing_dirs:
        return {"deleted": 0}

    deleted = 0
    for f in _iter_cache_files(existing_dirs):
        try:
            f.unlink()
            deleted += 1
        except Exception as e:
            logger.error(f"删除缓存文件失败 {f.name}: {e}")

    for cache_dir in existing_dirs:
        for d in sorted(cache_dir.rglob("*"), key=lambda p: len(p.parts), reverse=True):
            if d.is_dir():
                try:
                    d.rmdir()
                except Exception:
                    pass

    return {"deleted": deleted, "dirs": [str(d) for d in cache_dirs]}


# ============== 长期记忆管理 ==============


class MemorySaveRequest(BaseModel):
    """保存记忆请求"""

    content: str


@router.get("/memory")
async def get_memory():
    """获取长期记忆内容"""
    try:
        content = read_long_term_memory()
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/memory")
async def save_memory(req: MemorySaveRequest):
    """保存长期记忆内容"""
    try:
        file_path = _get_memory_file()
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(req.content, encoding="utf-8")
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
