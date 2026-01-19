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

from app.core.config import settings
from app.models.chat import ModelInfo, ModelsResponse

router = APIRouter()

# 设置文件路径
SETTINGS_FILE = Path("config/user_settings.json")


# ============== 模型名称格式化 ==============


def format_model_name(model_id: str) -> str:
    """
    格式化模型 ID 为显示名称
    规则：首字母大写，将 - 替换为空格
    
    示例：
    - gpt-4o -> Gpt 4o
    - claude-sonnet-4-5 -> Claude Sonnet 4 5
    - deepseek-v3 -> Deepseek V3
    """
    # 将 - 替换为空格，然后每个单词首字母大写
    words = model_id.split('-')
    formatted_words = [word.capitalize() for word in words]
    return ' '.join(formatted_words)


def load_user_settings() -> dict:
    """加载用户设置"""
    try:
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
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
                
                enabled_models.append(
                    ModelInfo(
                        id=model_id,
                        name=model_name,
                        provider=provider_name
                    )
                )
    
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

