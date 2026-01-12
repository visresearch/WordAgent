"""
聊天历史记录 API 路由
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List, Any

from app.core.db import get_db
from app.services.chat_history import ChatHistoryService


router = APIRouter()


# ============== 请求/响应模型 ==============

class SaveMessageRequest(BaseModel):
    """保存消息请求"""
    docId: str  # 文档唯一标识符
    docName: Optional[str] = None  # 文档名称
    role: str  # user / assistant
    content: str  # 消息内容
    documentJson: Optional[Any] = None  # AI 生成的文档 JSON
    selectionContext: Optional[dict] = None  # 选区上下文
    model: Optional[str] = None  # 使用的模型
    mode: Optional[str] = None  # 使用的模式


class HistoryResponse(BaseModel):
    """历史记录响应"""
    success: bool
    messages: List[dict] = []
    error: Optional[str] = None


class DocumentsResponse(BaseModel):
    """文档列表响应"""
    success: bool
    documents: List[dict] = []
    error: Optional[str] = None


class CommonResponse(BaseModel):
    """通用响应"""
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None


# ============== API 路由 ==============

@router.get("/history/{doc_id}", response_model=HistoryResponse)
async def get_chat_history(
    doc_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """
    获取指定文档的聊天历史
    
    Args:
        doc_id: 文档唯一标识符
        limit: 返回消息数量限制（默认50，最大200）
        offset: 偏移量
    """
    try:
        service = ChatHistoryService(db)
        messages = await service.get_history(doc_id, limit, offset)
        return HistoryResponse(success=True, messages=messages)
    except Exception as e:
        return HistoryResponse(success=False, messages=[], error=str(e))


@router.post("/history/save", response_model=CommonResponse)
async def save_message(
    request: SaveMessageRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    保存聊天消息
    """
    try:
        service = ChatHistoryService(db)
        await service.add_message(
            doc_id=request.docId,
            role=request.role,
            content=request.content,
            document_json=request.documentJson,
            selection_context=request.selectionContext,
            model=request.model,
            mode=request.mode,
            doc_name=request.docName
        )
        return CommonResponse(success=True, message="消息已保存")
    except Exception as e:
        return CommonResponse(success=False, error=str(e))


@router.delete("/history/{doc_id}", response_model=CommonResponse)
async def clear_history(
    doc_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    清空指定文档的聊天历史
    """
    try:
        service = ChatHistoryService(db)
        success = await service.clear_history(doc_id)
        if success:
            return CommonResponse(success=True, message="历史记录已清空")
        else:
            return CommonResponse(success=False, error="文档不存在")
    except Exception as e:
        return CommonResponse(success=False, error=str(e))


@router.get("/documents", response_model=DocumentsResponse)
async def get_documents(
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db)
):
    """
    获取所有有聊天记录的文档列表
    """
    try:
        service = ChatHistoryService(db)
        documents = await service.get_all_documents(limit)
        return DocumentsResponse(success=True, documents=documents)
    except Exception as e:
        return DocumentsResponse(success=False, documents=[], error=str(e))
