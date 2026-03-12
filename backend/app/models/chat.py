"""
聊天相关的数据模型
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel


class ModeEnum(str, Enum):
    """模式枚举"""

    agent = "agent"
    plan = "plan"


class ChatRequest(BaseModel):
    """聊天请求模型"""

    message: str  # 用户消息
    mode: ModeEnum  # 模式：agent 或 plan（必选）
    history: list[Any] = []  # 历史消息
    model: str = "gpt-4"  # 模型
    timestamp: int | None = None  # 时间戳
    documentJson: Any | None = None  # 文档 JSON 数据


class ChatResponse(BaseModel):
    """聊天响应模型"""

    success: bool
    message: str
    data: Any | None = None


class ModelInfo(BaseModel):
    """模型信息"""

    id: str  # 模型ID
    name: str  # 显示名称
    provider: str = ""  # 提供商
    description: str = ""  # 描述


class ModelsResponse(BaseModel):
    """模型列表响应"""

    success: bool
    models: list[ModelInfo]
