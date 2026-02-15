"""
多平台模型聚合接口
支持 OpenAI、智谱等多个平台，通过白名单过滤模型
"""

import asyncio
import json
from pathlib import Path

from fastapi import APIRouter
from openai import AsyncOpenAI
from pydantic import BaseModel

from app.models.chat import ModelInfo, ModelsResponse

router = APIRouter()

# 设置文件路径
SETTINGS_FILE = Path("config/user_settings.json")


# ============== 模型名称格式化 ==============

# 需要全大写的前缀/品牌词
UPPERCASE_WORDS = {"gpt", "glm", "dall", "llama", "yi", "ernie", "ppt", "cogview", "embedding"}


def format_model_name(model_id: str) -> str:
    """
    格式化模型 ID 为显示名称

    规则：
    1. 特定品牌词全大写：gpt -> GPT, glm -> GLM
    2. 其他词首字母大写：claude -> Claude, sonnet -> Sonnet
    3. 版本号连字符转点号：4-5 -> 4.5
    4. 保留数字和字母的连接：4o -> 4o

    示例：
    - gpt-4o -> GPT-4o
    - gpt-4o-mini -> GPT-4o Mini
    - glm-4-flash -> GLM-4 Flash
    - claude-sonnet-4-5 -> Claude Sonnet 4.5
    - deepseek-v3 -> Deepseek V3
    - qwen-turbo -> QWEN Turbo
    """
    import re

    # 按 - 分割
    parts = model_id.split("-")
    result_parts = []
    i = 0

    while i < len(parts):
        part = parts[i]

        # 检查是否是需要全大写的词
        if part.lower() in UPPERCASE_WORDS:
            result_parts.append(part.upper())
        # 检查是否是纯数字，可能是版本号的一部分
        elif part.isdigit() and i + 1 < len(parts) and parts[i + 1].isdigit():
            # 将 "4-5" 这样的版本号合并为 "4.5"
            result_parts.append(f"{part}.{parts[i + 1]}")
            i += 1  # 跳过下一个部分
        # 检查是否是数字开头（如 4o, 3.5）
        elif re.match(r"^\d", part):
            # 如果前一个是大写词，用连字符连接（如 GPT-4o）
            if result_parts and result_parts[-1].isupper():
                result_parts[-1] = result_parts[-1] + "-" + part
            else:
                result_parts.append(part)
        else:
            # 普通词首字母大写
            result_parts.append(part.capitalize())

        i += 1

    return " ".join(result_parts)


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


def get_enabled_models_from_settings() -> list[ModelInfo]:
    """
    从用户设置中获取已启用的模型
    """
    settings_data = load_user_settings()
    enabled_models = []

    for provider in settings_data.get("providers", []):
        if not provider.get("enabled", True):
            continue

        provider_name = provider.get("name", "Unknown")

        for model in provider.get("models", []):
            if model.get("enabled", False):
                model_id = model.get("id", "")
                model_name = model.get("name") or format_model_name(model_id)

                enabled_models.append(ModelInfo(id=model_id, name=model_name, provider=provider_name))

    # 按模型 ID 字母顺序排序
    enabled_models.sort(key=lambda m: m.id.lower())
    return enabled_models


# ============== API 路由 ==============


@router.get("/models", response_model=ModelsResponse)
async def get_models():
    """
    获取用户启用的模型列表
    从用户设置中读取已添加且启用的模型
    """
    try:
        models = get_enabled_models_from_settings()

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
    刷新模型列表（重新从设置文件读取）
    """
    models = get_enabled_models_from_settings()
    return {"success": True, "message": f"已刷新，共 {len(models)} 个可用模型"}


class ProviderModelsRequest(BaseModel):
    """获取 Provider 模型列表的请求体"""

    base_url: str
    api_key: str


def normalize_base_url(base_url: str) -> str:
    """
    标准化 base_url
    - 移除末尾的 /
    - 如果没有版本后缀（如 /v1），自动添加 /v1
    """
    url = base_url.rstrip("/")

    # 检查是否已有版本后缀（如 /v1, /v2 等）
    import re

    if not re.search(r"/v\d+$", url):
        url = url + "/v1"

    return url


@router.post("/providers/models")
async def get_provider_models(request: ProviderModelsRequest):
    """
    获取指定 Provider 的可用模型列表
    通过调用 OpenAI 兼容的 /models 接口获取
    """
    try:
        # 标准化 base_url（自动补全 /v1）
        base_url = normalize_base_url(request.base_url)
        print(f"📡 获取模型列表: {base_url}")

        # 创建 OpenAI 客户端
        client = AsyncOpenAI(
            base_url=base_url,
            api_key=request.api_key,
        )

        # 获取模型列表
        models_response = await client.models.list()

        # 转换为统一格式
        models = []
        for model in models_response.data:
            models.append(
                {"id": model.id, "name": format_model_name(model.id), "owned_by": getattr(model, "owned_by", "unknown")}
            )

        # 按模型 ID 字母顺序排序
        models.sort(key=lambda m: m["id"].lower())
        return {"success": True, "models": models}

    except Exception as e:
        print(f"❌ 获取 Provider 模型列表失败: {e}")
        return {"success": False, "error": str(e), "models": []}
