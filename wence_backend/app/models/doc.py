"""
文档相关的数据模型
"""

from pydantic import BaseModel
from typing import Optional, Any


class DocModifyRequest(BaseModel):
    """文档修改请求模型"""
    documentJson: Any  # 文档 JSON 数据
    question: str  # 用户问题/指令
    timestamp: Optional[int] = None  # 时间戳


class DocModifyResponse(BaseModel):
    """文档修改响应模型"""
    success: bool
    message: str
    modifiedJson: Optional[Any] = None
