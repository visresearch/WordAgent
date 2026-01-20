"""
设置管理接口
保存和加载用户的大模型配置
"""

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

# 设置文件路径
SETTINGS_FILE = Path("config/user_settings.json")


class ProviderConfig(BaseModel):
    """提供商配置"""
    name: str
    baseUrl: str
    apiKey: str
    models: list[dict[str, Any]] = []
    enabled: bool = True


class UserSettings(BaseModel):
    """用户设置"""
    providers: list[ProviderConfig] = []


@router.get("/settings")
async def get_settings() -> UserSettings:
    """获取用户设置"""
    try:
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
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
        
        # 保存设置
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings.model_dump(), f, ensure_ascii=False, indent=2)
        
        return {"message": "设置保存成功"}
    except Exception as e:
        print(f"保存设置失败: {e}")
        raise HTTPException(status_code=500, detail=f"保存设置失败: {str(e)}")
