"""
聊天相关的数据模型
"""

from pydantic import BaseModel
from typing import Optional, Any, List


class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str  # 用户消息
    history: List[Any] = []  # 历史消息
    model: str = "gpt-4"  # 模型
    timestamp: Optional[int] = None  # 时间戳
    documentJson: Optional[Any] = None  # 文档 JSON 数据


class ChatResponse(BaseModel):
    """聊天响应模型"""
    success: bool
    message: str
    data: Optional[Any] = None
