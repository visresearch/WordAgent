"""
多平台 LLM 客户端管理
根据模型 ID 自动选择对应的 API 配置
从用户设置文件读取 provider 配置
"""

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

from openai import AsyncOpenAI

from app.core.config import get_user_settings_file

# ============== 配置文件路径 ==============

SETTINGS_FILE = get_user_settings_file()


# ============== 数据结构 ==============


@dataclass
class LLMProvider:
    """LLM 提供商配置"""

    name: str
    api_key: str
    base_url: str
    models: list[dict]  # 该 provider 下的模型列表


# ============== 配置读取 ==============


def load_user_settings() -> dict:
    """加载用户设置"""
    try:
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"providers": []}
    except Exception as e:
        print(f"加载用户设置失败: {e}")
        return {"providers": []}


def normalize_base_url(base_url: str) -> str:
    """
    标准化 base_url
    - 移除末尾的 /
    - 如果没有版本后缀（如 /v1），自动添加 /v1
    """
    url = base_url.rstrip("/")

    # 检查是否已有版本后缀（如 /v1, /v2 等）
    if not re.search(r"/v\d+$", url):
        url = url + "/v1"

    return url


def get_providers_from_settings() -> dict[str, LLMProvider]:
    """从用户设置中获取所有已启用的提供商配置"""
    settings = load_user_settings()
    providers = {}

    for provider_data in settings.get("providers", []):
        if not provider_data.get("enabled", True):
            continue

        name = provider_data.get("name", "").lower()
        if not name:
            continue

        providers[name] = LLMProvider(
            name=provider_data.get("name", ""),
            api_key=provider_data.get("apiKey", ""),
            base_url=normalize_base_url(provider_data.get("baseUrl", "")),
            models=provider_data.get("models", []),
        )

    return providers


def find_provider_for_model(model_id: str) -> tuple[LLMProvider | None, str]:
    """
    根据模型 ID 找到对应的提供商

    Returns:
        (provider, actual_model_id) - 提供商配置和实际模型ID
    """
    providers = get_providers_from_settings()

    # 遍历所有 provider，查找包含该模型的 provider
    for provider_name, provider in providers.items():
        for model in provider.models:
            if model.get("id") == model_id and model.get("enabled", False):
                return provider, model_id

    # 如果没找到精确匹配，返回 None
    return None, model_id


def get_first_available_model() -> tuple[LLMProvider | None, str]:
    """获取第一个可用的模型"""
    providers = get_providers_from_settings()

    for provider_name, provider in providers.items():
        for model in provider.models:
            if model.get("enabled", False):
                return provider, model.get("id", "")

    return None, ""


def get_temperature() -> float:
    """从用户设置中获取 temperature 值"""
    settings = load_user_settings()
    return settings.get("temperature", 0.7)


def get_custom_prompt() -> str:
    """从 user_settings.json 读取用户自定义 Prompt"""
    try:
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("customPrompt", "") or ""
    except Exception as e:
        print(f"读取 customPrompt 失败: {e}")
    return ""


def get_proxy_config() -> dict:
    """从用户设置中获取代理配置

    Returns:
        {"enabled": bool, "host": str, "port": int}
    """
    settings = load_user_settings()
    proxy = settings.get("proxy", {})
    return {
        "enabled": proxy.get("enabled", False),
        "host": proxy.get("host", ""),
        "port": proxy.get("port", 0),
    }


def get_proxy_url() -> str | None:
    """根据 host + port 构建 http 代理 URL，未启用则返回 None"""
    cfg = get_proxy_config()
    if cfg["enabled"] and cfg["host"] and cfg["port"]:
        return f"http://{cfg['host']}:{cfg['port']}"
    return None


def get_http_proxy_url() -> str | None:
    """获取 http 代理 URL，未启用则返回 None"""
    return get_proxy_url()


def get_https_proxy_url() -> str | None:
    """获取 https 代理 URL，未启用则返回 None"""
    return get_proxy_url()


def get_httpx_proxy_url() -> str | None:
    """获取 httpx 使用的单一代理 URL，未启用则返回 None"""
    return get_proxy_url()


def create_llm(model_name: str):
    """创建 LangChain ChatOpenAI 实例。"""
    from langchain_openai import ChatOpenAI

    actual_model_name = resolve_model(model_name)
    provider_info = LLMClientManager.get_provider_info(actual_model_name)

    if not provider_info:
        raise ValueError(f"未找到模型 {actual_model_name} 对应的提供商配置，请在设置中添加")

    if not provider_info.api_key:
        raise ValueError(f"提供商 {provider_info.name} 未配置 API Key")

    # 获取代理配置
    proxy_url = get_https_proxy_url() or get_http_proxy_url()

    # 当用户未启用代理时，临时清除环境变量中的代理设置
    # 防止 openai/httpx 读取到系统的 socks:// 代理导致 scheme 不支持报错
    _proxy_env_keys = [
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
    ]
    saved_env = {}
    if not proxy_url:
        for key in _proxy_env_keys:
            if key in os.environ:
                saved_env[key] = os.environ.pop(key)

    try:
        import httpx

        http_client = httpx.Client(proxy=proxy_url)
        http_async_client = httpx.AsyncClient(proxy=proxy_url)

        return ChatOpenAI(
            model=actual_model_name,
            openai_api_key=provider_info.api_key,
            openai_api_base=provider_info.base_url,
            temperature=get_temperature(),
            max_tokens=16384,
            streaming=True,
            http_client=http_client,
            http_async_client=http_async_client,
        )
    finally:
        # 恢复环境变量
        os.environ.update(saved_env)


class LLMClientManager:
    """LLM 客户端管理器"""

    _clients: dict[str, AsyncOpenAI] = {}

    @classmethod
    def get_client(cls, model_id: str) -> AsyncOpenAI:
        """
        根据模型 ID 获取对应的 AsyncOpenAI 客户端

        Args:
            model_id: 模型 ID，如 "gpt-4o", "glm-4.5"

        Returns:
            配置好的 AsyncOpenAI 客户端
        """
        # 解析模型，处理 auto
        actual_model_id = cls.resolve_model(model_id)

        # 查找对应的 provider
        provider, _ = find_provider_for_model(actual_model_id)

        if not provider:
            raise ValueError(f"未找到模型 {actual_model_id} 对应的提供商配置，请在设置中添加")

        if not provider.api_key:
            raise ValueError(f"提供商 {provider.name} 未配置 API Key")

        # 获取代理配置
        proxy_url = get_proxy_url()

        # 使用 provider name + base_url + proxy 作为缓存 key
        cache_key = f"{provider.name}:{provider.base_url}:{proxy_url or ''}"

        # 使用缓存
        if cache_key in cls._clients:
            return cls._clients[cache_key]

        # 创建新客户端
        import httpx as _httpx

        http_client = _httpx.AsyncClient(proxy=proxy_url) if proxy_url else None
        client = AsyncOpenAI(
            api_key=provider.api_key,
            base_url=provider.base_url,
            http_client=http_client,
        )

        cls._clients[cache_key] = client
        return client

    @classmethod
    def get_provider_info(cls, model_id: str) -> LLMProvider | None:
        """获取模型对应的提供商信息"""
        actual_model_id = cls.resolve_model(model_id)
        provider, _ = find_provider_for_model(actual_model_id)
        return provider

    @classmethod
    def get_default_model(cls) -> str:
        """获取默认模型（第一个启用的模型）"""
        provider, model_id = get_first_available_model()
        if model_id:
            return model_id
        # 兜底返回
        return "gpt-4o"

    @classmethod
    def resolve_model(cls, model_id: str | None) -> str:
        """
        解析模型 ID，处理 auto 和空值

        Args:
            model_id: 用户指定的模型 ID，可能是 "auto" 或具体模型

        Returns:
            实际使用的模型 ID
        """
        if not model_id or model_id == "auto":
            return cls.get_default_model()
        return model_id

    @classmethod
    def clear_cache(cls):
        """清除客户端缓存（配置变更后调用）"""
        cls._clients.clear()


# ============== 便捷函数 ==============


def get_llm_client(model_id: str) -> AsyncOpenAI:
    """获取 LLM 客户端的便捷函数"""
    return LLMClientManager.get_client(model_id)


def resolve_model(model_id: str | None) -> str:
    """解析模型 ID 的便捷函数"""
    return LLMClientManager.resolve_model(model_id)
