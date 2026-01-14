"""
多平台模型聚合接口
支持 OpenAI、智谱等多个平台，通过白名单过滤模型
"""

import asyncio

from fastapi import APIRouter
from openai import AsyncOpenAI

from app.core.config import settings
from app.models.chat import ModelInfo, ModelsResponse

router = APIRouter()


# ============== 模型白名单配置 ==============
# 格式: "模型ID": {"name": "显示名称", "provider": "提供商"}
# 如果模型不在白名单中，将被过滤掉

MODEL_WHITELIST: dict[str, dict[str, str]] = {
    # OpenAI 系列
    "gpt-4o": {"name": "GPT-4o", "provider": "OpenAI"},
    "gpt-5-mini": {"name": "GPT-5 mini", "provider": "OpenAI"},
    "gpt-4-turbo": {"name": "GPT-4 Turbo", "provider": "OpenAI"},
    "gpt-5": {"name": "GPT-5", "provider": "OpenAI"},
    "gpt-5.1": {"name": "GPT-5.1", "provider": "OpenAI"},
    "gpt-5.2": {"name": "GPT-5.2", "provider": "OpenAI"},
    # Claude 系列
    "claude-haiku-4-5-20251001": {"name": "Claude Haiku 4.5", "provider": "Anthropic"},
    "claude-haiku-4-5-20251001-thinking": {"name": "Claude Haiku 4.5 Thinking", "provider": "Anthropic"},
    "claude-sonnet-4-5-20250929": {"name": "Claude Sonnet 4.5", "provider": "Anthropic"},
    "claude-sonnet-4-5-20250929-thinking": {"name": "Claude Sonnet 4.5 Thinking", "provider": "Anthropic"},
    "claude-opus-4-20250514-thinking": {"name": "Claude Opus 4 Thinking", "provider": "Anthropic"},
    "claude-opus-4-20250514": {"name": "Claude Opus 4", "provider": "Anthropic"},
    "claude-opus-4-5-20251101": {"name": "Claude Opus 4.5", "provider": "Anthropic"},
    # Gemini 系列
    "gemini-2.5-pro": {"name": "Gemini 2.5 Pro", "provider": "Google"},
    "gemini-2.5-flash": {"name": "Gemini 2.5 Flash", "provider": "Google"},
    "gemini-3-pro-preview": {"name": "Gemini 3 Pro Preview", "provider": "Google"},
    # DeepSeek 系列
    "deepseek-r1": {"name": "DeepSeek R1", "provider": "DeepSeek"},
    "deepseek-v3": {"name": "DeepSeek V3", "provider": "DeepSeek"},
    "deepseek-v3.2-thinking": {"name": "DeepSeek V3.2 Thinking", "provider": "DeepSeek"},
    # 智谱 GLM 系列
    "glm-4.5": {"name": "GLM-4.5", "provider": "智谱AI"},
    "glm-4.5-air": {"name": "GLM-4.5 Air", "provider": "智谱AI"},
    "glm-4.6": {"name": "GLM-4.6", "provider": "智谱AI"},
    "glm-4.7": {"name": "GLM-4.7", "provider": "智谱AI"},
}


# ============== 平台配置 ==============


class PlatformConfig:
    """平台配置"""

    def __init__(self, name: str, api_key: str, base_url: str, enabled: bool = True):
        self.name = name
        self.api_key = api_key
        self.base_url = base_url
        self.enabled = enabled and bool(api_key)  # 没有 API Key 则禁用


def get_platforms() -> list[PlatformConfig]:
    """获取所有平台配置"""
    # 处理 OpenAI base_url，确保以 /v1 结尾
    openai_base_url = settings.OPENAI_BASE_URL or "https://api.openai.com/v1"
    if not openai_base_url.endswith("/v1") and not openai_base_url.endswith("/v1/"):
        openai_base_url = openai_base_url.rstrip("/") + "/v1"

    return [
        PlatformConfig(name="OpenAI", api_key=settings.OPENAI_API_KEY, base_url=openai_base_url),
        # 智谱使用 OpenAI 兼容接口
        PlatformConfig(name="智谱AI", api_key=settings.ZHIPU_API_KEY, base_url="https://open.bigmodel.cn/api/paas/v4/"),
        # 可以继续添加更多平台...
    ]


# ============== 模型获取逻辑 ==============


async def fetch_models_from_platform(platform: PlatformConfig) -> list[str]:
    """
    从单个平台获取模型列表
    返回模型 ID 列表
    """
    if not platform.enabled:
        return []

    try:
        client = AsyncOpenAI(api_key=platform.api_key, base_url=platform.base_url)

        models = await client.models.list()
        model_ids = [m.id for m in models.data]
        print(f"✅ [{platform.name}] 获取到 {len(model_ids)} 个模型")
        return model_ids

    except Exception as e:
        print(f"⚠️ [{platform.name}] 获取模型失败: {e}")
        return []


async def fetch_all_models() -> list[ModelInfo]:
    """
    从所有平台获取模型，并通过白名单过滤
    顺序严格按照白名单定义的顺序
    """
    platforms = get_platforms()

    # 并发获取所有平台的模型
    tasks = [fetch_models_from_platform(p) for p in platforms]
    results = await asyncio.gather(*tasks)

    # 合并所有模型 ID（去重）
    all_model_ids = set()
    for model_ids in results:
        all_model_ids.update(model_ids)

    print(f"📊 共获取到 {len(all_model_ids)} 个模型（去重后）")

    # 按白名单顺序过滤（保持白名单中定义的顺序）
    filtered_models = []
    for model_id, config in MODEL_WHITELIST.items():
        if model_id in all_model_ids:
            filtered_models.append(
                ModelInfo(id=model_id, name=config["name"], provider=config["provider"], description="")
            )

    print(f"✅ 白名单过滤后剩余 {len(filtered_models)} 个模型")
    return filtered_models


# ============== 缓存机制 ==============

_models_cache: list[ModelInfo] | None = None
_cache_time: float = 0
CACHE_DURATION = 300  # 缓存 5 分钟


async def get_cached_models() -> list[ModelInfo]:
    """获取模型列表（带缓存）"""
    global _models_cache, _cache_time

    import time

    current_time = time.time()

    # 检查缓存是否有效
    if _models_cache is not None and (current_time - _cache_time) < CACHE_DURATION:
        return _models_cache

    # 重新获取
    _models_cache = await fetch_all_models()
    _cache_time = current_time

    return _models_cache


# ============== API 路由 ==============


@router.get("/models", response_model=ModelsResponse)
async def get_models():
    """
    获取可用模型列表（聚合多平台 + 白名单过滤）
    """
    try:
        models = await get_cached_models()

        # 在列表开头添加 Auto 选项
        auto_model = ModelInfo(id="auto", name="Auto", provider="WenCe AI", description="自动选择最佳模型")

        return ModelsResponse(success=True, models=[auto_model] + models)
    except Exception as e:
        print(f"❌ 获取模型列表失败: {e}")
        # 失败时返回默认模型
        return ModelsResponse(
            success=True,
            models=[ModelInfo(id="auto", name="Auto", provider="WenCe AI", description="自动选择最佳模型")],
        )


@router.post("/models/refresh")
async def refresh_models():
    """
    强制刷新模型缓存
    """
    global _models_cache, _cache_time
    _models_cache = None
    _cache_time = 0

    models = await get_cached_models()
    return {"success": True, "message": f"已刷新，共 {len(models)} 个可用模型"}
