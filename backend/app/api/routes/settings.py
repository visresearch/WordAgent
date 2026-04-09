"""
设置管理接口
保存和加载用户的大模型配置
"""

import json
import os
import shutil
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.config import get_user_settings_file

router = APIRouter()

# 设置文件路径
SETTINGS_FILE = get_user_settings_file()


class ProviderConfig(BaseModel):
    """提供商配置"""

    name: str
    baseUrl: str
    apiKey: str
    apiType: str = "openai"  # openai / anthropic
    models: list[dict[str, Any]] = []
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
    proofreadMode: str = "revision"
    # 代理设置
    proxy: ProxyConfig = ProxyConfig()
    # 个性化设置
    customPrompt: str = ""
    temperature: float = 0.7
    # MCP 服务器设置
    mcpServers: list[dict[str, Any]] = []


class MCPServerTestRequest(BaseModel):
    """MCP 服务器连接测试请求"""

    name: str = ""
    config: dict[str, Any] | str


@router.get("/settings")
async def get_settings():
    """获取用户设置"""
    try:
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return UserSettings(**data)
        # 返回默认设置
        return UserSettings()
    except Exception as e:
        print(f"读取设置失败: {e}")
        return UserSettings()


@router.post("/settings")
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
        merged = {**existing_data, **settings.model_dump(exclude_unset=True)}

        # 保存设置
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)

        # 清除 LLM 客户端缓存，使代理等配置变更生效
        try:
            from app.services.llm_client import LLMClientManager

            LLMClientManager.clear_cache()
        except Exception:
            pass

        return {"message": "设置保存成功"}
    except Exception as e:
        print(f"保存设置失败: {e}")
        raise HTTPException(status_code=500, detail=f"保存设置失败: {str(e)}")


@router.post("/settings/mcp/test")
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
            headers = config.get("headers") if isinstance(config.get("headers"), dict) else {}

            try:
                async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                    # MCP 服务实际可能不支持 GET；这里只验证网络可达和服务有响应
                    resp = await client.get(url, headers=headers)
                return {
                    "success": True,
                    "message": f"{server_name} 连接成功 (HTTP {resp.status_code})",
                }
            except Exception as e:
                return {
                    "success": False,
                    "message": f"{server_name} 连接失败: {str(e)}",
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


# ============== WPS 缓存路径 ==============


def _get_wps_cache_dir() -> Path | None:
    """获取 WPS 图片缓存目录"""
    home = Path.home()

    # Linux WPS 模板目录
    linux_path = home / ".local/share/Kingsoft/office6/templates/wps/zh_CN"
    if linux_path.exists():
        return linux_path

    # Windows WPS 模板目录
    appdata = os.environ.get("APPDATA", "")
    if appdata:
        win_path = Path(appdata) / "kingsoft/wps/templates/wps/zh_CN"
        if win_path.exists():
            return win_path

    return None


@router.get("/cache/scan")
async def scan_cache():
    """扫描 WPS 图片缓存"""
    cache_dir = _get_wps_cache_dir()

    if not cache_dir or not cache_dir.exists():
        return {"dir": "", "fileCount": 0, "totalSize": 0}

    count = 0
    total_size = 0
    for f in cache_dir.iterdir():
        if f.is_file() and f.name.startswith("wps_img_") and f.name.endswith(".png"):
            count += 1
            total_size += f.stat().st_size

    return {"dir": str(cache_dir), "fileCount": count, "totalSize": total_size}


@router.delete("/cache/clear")
async def clear_cache():
    """清除 WPS 图片缓存"""
    cache_dir = _get_wps_cache_dir()

    if not cache_dir or not cache_dir.exists():
        return {"deleted": 0}

    deleted = 0
    for f in cache_dir.iterdir():
        if f.is_file() and f.name.startswith("wps_img_") and f.name.endswith(".png"):
            try:
                f.unlink()
                deleted += 1
            except Exception as e:
                print(f"删除缓存文件失败 {f.name}: {e}")

    return {"deleted": deleted}
