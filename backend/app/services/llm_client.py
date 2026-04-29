"""
多平台 LLM 客户端管理
根据模型 ID 自动选择对应的 API 配置
从用户设置文件读取 provider 配置
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path

from openai import AsyncOpenAI

from app.core.config import get_user_settings_file

from langchain_openai import ChatOpenAI as _BaseChatOpenAI
from langchain_core.outputs import ChatGenerationChunk


class ChatOpenAI(_BaseChatOpenAI):
    """支持 reasoning_content 的 ChatOpenAI 子类。

    LangChain 底层不映射 reasoning_content 到 additional_kwargs，
    这个子类在流式处理时从原始 chunk 中提取 reasoning_content，
    注入到 AIMessageChunk.additional_kwargs["reasoning_content"] 中，
    使其可以被 agent 流式处理代码正确获取。
    """

    def _convert_chunk_to_generation_chunk(self, chunk, default_chunk_class, base_generation_info=None):
        generation_chunk = super()._convert_chunk_to_generation_chunk(chunk, default_chunk_class, base_generation_info)
        if generation_chunk is None:
            return None

        # 从原始 chunk 中提取 reasoning_content
        choices = chunk.get("choices", []) or chunk.get("chunk", {}).get("choices", [])
        if choices:
            delta = choices[0].get("delta", {})
            reasoning_content = delta.get("reasoning_content")
            if reasoning_content:
                msg = generation_chunk.message
                if hasattr(msg, "additional_kwargs"):
                    msg.additional_kwargs["reasoning_content"] = reasoning_content

        return generation_chunk


def init_chat_model_with_reasoning(model_name: str, enable_thinking: bool = False):
    """
    创建支持 reasoning_content 的 ChatOpenAI 实例。

    等价于 langchain.chat_models.init_chat_model，但使用自定义的
    ChatOpenAI 子类，能在流式处理中正确提取 reasoning_content。
    仅用于 OpenAI 兼容接口。Anthropic 模型走 init_chat_model。
    """
    kwargs = get_llm_init_kwargs(model_name, enable_thinking=enable_thinking)
    model_provider = kwargs.pop("model_provider", None)

    # Anthropic 模型走标准 init_chat_model（内部会路由到 ChatAnthropic）
    if model_provider == "anthropic":
        return _init_chat_model_fallback(model_name, kwargs, enable_thinking)

    # OpenAI 兼容接口：thinking 需要从顶层移到 extra_body
    if "thinking" in kwargs:
        thinking_cfg = kwargs.pop("thinking")
        extra_body = kwargs.get("extra_body") or {}
        extra_body["thinking"] = thinking_cfg
        kwargs["extra_body"] = extra_body

    return ChatOpenAI(**kwargs)


def _init_chat_model_fallback(model_name: str, kwargs: dict, enable_thinking: bool):
    """Anthropic 模型走 init_chat_model，不做额外处理"""
    from langchain.chat_models import init_chat_model as _init_chat_model

    return _init_chat_model(
        model=kwargs.pop("model"),
        model_provider="anthropic",
        api_key=kwargs.pop("api_key"),
        base_url=kwargs.pop("base_url", None) or None,
        temperature=kwargs.pop("temperature"),
        max_tokens=kwargs.pop("max_tokens"),
        streaming=kwargs.pop("streaming"),
        http_client=kwargs.pop("http_client", None),
        http_async_client=kwargs.pop("http_async_client", None),
        thinking=kwargs.pop("thinking", None) if enable_thinking else None,
        # 剩余参数透传
        **kwargs,
    )


# ============== 配置文件路径 ==============

SETTINGS_FILE = get_user_settings_file()


# ============== 数据结构 ==============


@dataclass
class LLMProvider:
    """LLM 提供商配置"""

    name: str
    api_key: str
    base_url: str
    api_type: str  # openai / anthropic
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
    url = (base_url or "").rstrip("/")
    if not url:
        return ""

    # 检查是否已有版本后缀（如 /v1, /v2 等）
    if not re.search(r"/v\d+$", url):
        url = url + "/v1"

    return url


def infer_api_type(model_id: str, base_url: str, configured_type: str = "") -> str:
    """推断 provider 的 API 类型。"""
    if configured_type in {"openai", "anthropic"}:
        return configured_type

    lowered_url = (base_url or "").lower()
    lowered_model = (model_id or "").lower()

    # 官方 Anthropic 域名优先走 ChatAnthropic
    if "anthropic.com" in lowered_url:
        return "anthropic"

    # 其余场景默认走 OpenAI 兼容接口（可承载 Claude 代理/中转）
    if lowered_model.startswith("claude") and "anthropic" in lowered_url:
        return "anthropic"
    return "openai"


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

        base_url_raw = provider_data.get("baseUrl", "")
        configured_api_type = str(provider_data.get("apiType", "")).strip().lower()

        # 先用首个可用模型辅助推断，未提供则留空
        first_model_id = ""
        for m in provider_data.get("models", []):
            if isinstance(m, dict) and m.get("enabled", True):
                first_model_id = str(m.get("id", ""))
                break

        api_type = infer_api_type(first_model_id, base_url_raw, configured_api_type)
        normalized_base_url = base_url_raw.rstrip("/") if api_type == "anthropic" else normalize_base_url(base_url_raw)

        providers[name] = LLMProvider(
            name=provider_data.get("name", ""),
            api_key=provider_data.get("apiKey", ""),
            base_url=normalized_base_url,
            api_type=api_type,
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


def get_reasoning_extra_body(model_name: str) -> dict | None:
    """
    返回 OpenAI 兼容模型的 reasoning/thinking extra_body 参数。

    通用的 thinking 注入参数，适用于任意 OpenAI 兼容 API
    （Qwen、DeepSeek、vLLM、OneAPI 等均支持）。
    API 不支持该参数时会忽略，不影响正常调用。
    """
    return {"thinking": {"type": "enabled", "parameters": {"effort": "high"}}}


def supports_thinking(model_name: str) -> bool:
    """
    检查模型是否支持 thinking 模式。
    目前对所有模型返回 True，因为 API 不支持时会自动忽略，不影响正常调用。
    """
    return True


def _resolve_llm_params(model_name: str, enable_thinking: bool = False) -> dict:
    """
    根据模型名解析出 init_chat_model 所需的全部参数（含 model、model_provider）。

    返回值可直接用于 init_chat_model(**params)。
    不处理环境变量清理/恢复（由调用方负责）。
    """
    actual_model_name = resolve_model(model_name)
    provider_info = LLMClientManager.get_provider_info(actual_model_name)

    if not provider_info:
        raise ValueError(f"未找到模型 {actual_model_name} 对应的提供商配置，请在设置中添加")

    if not provider_info.api_key:
        raise ValueError(f"提供商 {provider_info.name} 未配置 API Key")

    effective_api_type = infer_api_type(actual_model_name, provider_info.base_url, provider_info.api_type)
    proxy_url = get_https_proxy_url() or get_http_proxy_url()

    kwargs: dict = {
        "model": actual_model_name,
        "api_key": provider_info.api_key,
        "temperature": get_temperature(),
        "max_tokens": 16384,
        "streaming": True,
    }

    if effective_api_type == "anthropic":
        kwargs["model_provider"] = "anthropic"
        if provider_info.base_url:
            kwargs["base_url"] = provider_info.base_url
        if proxy_url:
            kwargs["anthropic_proxy"] = proxy_url
        if enable_thinking:
            lowered = actual_model_name.lower()
            if "opus-4" in lowered:
                kwargs["thinking"] = {"type": "enabled", "budget_tokens": 10000}
                kwargs["temperature"] = 1
                print(f"[LLM] 🧠 Anthropic thinking (opus-4): budget=10000")
            elif "sonnet-4" in lowered:
                kwargs["thinking"] = {"type": "enabled", "budget_tokens": 8000}
                kwargs["temperature"] = 1
                print(f"[LLM] 🧠 Anthropic thinking (sonnet-4): budget=8000")
            elif "3-5-sonnet" in lowered:
                kwargs["thinking"] = {"type": "enabled", "budget_tokens": 8000}
                kwargs["temperature"] = 1
                print(f"[LLM] 🧠 Anthropic thinking (3.5-sonnet): budget=8000")
    else:
        kwargs["model_provider"] = "openai"
        kwargs["base_url"] = provider_info.base_url
        if proxy_url:
            import httpx

            kwargs["http_client"] = httpx.Client(proxy=proxy_url)
            kwargs["http_async_client"] = httpx.AsyncClient(proxy=proxy_url)
        if enable_thinking:
            kwargs["extra_body"] = get_reasoning_extra_body(actual_model_name)
            print(f"[LLM] 🧠 已注入 thinking extra_body（模型不支持则自动忽略）")

    return kwargs


def get_llm_init_kwargs(model_name: str, enable_thinking: bool = False) -> dict:
    """
    获取 init_chat_model 所需的完整参数字典。

    用法: init_chat_model(**get_llm_init_kwargs("gpt-4o"))
    """
    return _resolve_llm_params(model_name, enable_thinking)


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
    def get_default_model(cls, provider: str = "") -> str:
        """获取默认模型（第一个启用的模型，可按提供商过滤）"""
        if provider:
            # 根据提供商获取模型
            provider_config = cls._get_provider_config(provider)
            if provider_config:
                models = provider_config.get("models", [])
                for model in models:
                    if model.get("enabled", False):
                        return model.get("id", "gpt-4o")

        # 如果没找到指定提供商的模型，尝试获取第一个启用的模型
        _, model_id = get_first_available_model()
        if model_id:
            return model_id
        # 兜底返回
        return "gpt-4o"

    @classmethod
    def _get_provider_config(cls, provider_name: str) -> dict | None:
        """根据提供商名称获取配置"""
        try:
            settings_data = load_user_settings()
            for p in settings_data.get("providers", []):
                if p.get("name") == provider_name:
                    return p
        except Exception:
            pass
        return None

    @classmethod
    def resolve_model(cls, model_id: str | None, provider: str = "") -> str:
        """
        解析模型 ID，处理 auto 和空值

        Args:
            model_id: 用户指定的模型 ID，可能是 "auto" 或具体模型
            provider: 模型提供商名称

        Returns:
            实际使用的模型 ID
        """
        if not model_id or model_id == "auto":
            return cls.get_default_model(provider)
        return model_id

    @classmethod
    def clear_cache(cls):
        """清除客户端缓存（配置变更后调用）"""
        cls._clients.clear()


# ============== 便捷函数 ==============


def get_llm_client(model_id: str) -> AsyncOpenAI:
    """获取 LLM 客户端的便捷函数"""
    return LLMClientManager.get_client(model_id)


def resolve_model(model_id: str | None, provider: str = "") -> str:
    """解析模型 ID 的便捷函数"""
    return LLMClientManager.resolve_model(model_id, provider)
