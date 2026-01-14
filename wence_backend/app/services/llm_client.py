"""
多平台 LLM 客户端管理
根据模型 ID 自动选择对应的 API 配置
"""

from dataclasses import dataclass

from openai import AsyncOpenAI

from app.core.config import settings

# ============== 平台配置 ==============


@dataclass
class LLMProvider:
    """LLM 提供商配置"""

    name: str
    api_key: str
    base_url: str
    default_model: str
    model_prefixes: list[str]  # 用于识别属于该平台的模型


# 模型 ID 到提供商的映射（精确匹配优先）
MODEL_TO_PROVIDER: dict[str, str] = {
    # OpenAI 系列
    "gpt-4o": "openai",
    "gpt-4-turbo": "openai",
    "gpt-5": "openai",
    "gpt-5-mini": "openai",
    "gpt-5.1": "openai",
    "gpt-5.2": "openai",
    # Claude 系列（通过 OpenAI 兼容接口）
    "claude-haiku-4-5-20251001": "openai",
    "claude-haiku-4-5-20251001-thinking": "openai",
    "claude-sonnet-4-5-20250929": "openai",
    "claude-sonnet-4-5-20250929-thinking": "openai",
    "claude-opus-4-20250514": "openai",
    "claude-opus-4-20250514-thinking": "openai",
    "claude-opus-4-5-20251101": "openai",
    # Gemini 系列（通过 OpenAI 兼容接口）
    "gemini-2.5-pro": "openai",
    "gemini-2.5-flash": "openai",
    "gemini-3-pro-preview": "openai",
    # DeepSeek 系列（通过 OpenAI 兼容接口）
    "deepseek-r1": "openai",
    "deepseek-v3": "openai",
    "deepseek-v3.2-thinking": "openai",
    # 智谱 GLM 系列
    "glm-4.5": "zhipu",
    "glm-4.5-air": "zhipu",
    "glm-4.6": "zhipu",
    "glm-4.7": "zhipu",
}


def get_providers() -> dict[str, LLMProvider]:
    """获取所有提供商配置"""

    # 处理 OpenAI base_url
    openai_base_url = settings.OPENAI_BASE_URL or "https://api.openai.com/v1"
    if not openai_base_url.endswith("/v1") and not openai_base_url.endswith("/v1/"):
        openai_base_url = openai_base_url.rstrip("/") + "/v1"

    return {
        "openai": LLMProvider(
            name="OpenAI",
            api_key=settings.OPENAI_API_KEY,
            base_url=openai_base_url,
            default_model=settings.OPENAI_DEFAULT_MODEL,
            model_prefixes=["gpt-", "o1-", "claude-", "gemini-", "deepseek-"],
        ),
        "zhipu": LLMProvider(
            name="智谱AI",
            api_key=settings.ZHIPU_API_KEY,
            base_url=settings.ZHIPU_BASE_URL,
            default_model=settings.ZHIPU_DEFAULT_MODEL,
            model_prefixes=["glm-", "chatglm-", "codegeex-"],
        ),
        "qwen": LLMProvider(
            name="千问AI",
            api_key=settings.QWEN_API_KEY,
            base_url=settings.QWEN_BASE_URL,
            default_model=settings.QWEN_DEFAULT_MODEL,
            model_prefixes=["qwen-"],
        ),
    }


def get_provider_for_model(model_id: str) -> str:
    """根据模型 ID 获取对应的提供商名称"""

    # 1. 精确匹配
    if model_id in MODEL_TO_PROVIDER:
        return MODEL_TO_PROVIDER[model_id]

    # 2. 前缀匹配
    providers = get_providers()
    for provider_name, provider in providers.items():
        for prefix in provider.model_prefixes:
            if model_id.lower().startswith(prefix.lower()):
                return provider_name

    # 3. 默认使用 OpenAI（因为很多第三方转发服务用 OpenAI 兼容接口）
    return "openai"


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
        provider_name = get_provider_for_model(model_id)

        # 使用缓存
        if provider_name in cls._clients:
            return cls._clients[provider_name]

        # 创建新客户端
        providers = get_providers()
        provider = providers.get(provider_name)

        if not provider:
            raise ValueError(f"未知的提供商: {provider_name}")

        if not provider.api_key:
            raise ValueError(f"提供商 {provider.name} 未配置 API Key")

        client = AsyncOpenAI(api_key=provider.api_key, base_url=provider.base_url)

        cls._clients[provider_name] = client
        return client

    @classmethod
    def get_provider_info(cls, model_id: str) -> LLMProvider:
        """获取模型对应的提供商信息"""
        provider_name = get_provider_for_model(model_id)
        providers = get_providers()
        return providers.get(provider_name)

    @classmethod
    def get_default_model(cls) -> str:
        """获取默认模型"""
        # 优先使用 OpenAI
        if settings.OPENAI_API_KEY:
            return settings.OPENAI_DEFAULT_MODEL
        # 其次使用智谱
        if settings.ZHIPU_API_KEY:
            return settings.ZHIPU_DEFAULT_MODEL
        # 默认
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
