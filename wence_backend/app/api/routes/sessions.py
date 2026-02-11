"""
会话管理 API 路由

提供 Session CRUD 和 Session 下的消息操作接口
"""

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.services.session_service import SessionService

router = APIRouter()


# ============== 请求/响应模型 ==============


class CreateSessionRequest(BaseModel):
    """创建会话请求"""

    docId: str | None = None
    docName: str | None = None
    title: str | None = "新对话"


class RenameSessionRequest(BaseModel):
    """重命名会话请求"""

    title: str


class AddMessageRequest(BaseModel):
    """添加消息请求"""

    role: str  # user / assistant
    content: str
    documentJson: Any | None = None
    selectionContext: dict | None = None
    contentParts: list[dict] | None = None
    model: str | None = None
    mode: str | None = None


class SessionResponse(BaseModel):
    """单个会话响应"""

    success: bool
    session: dict | None = None
    error: str | None = None


class SessionListResponse(BaseModel):
    """会话列表响应"""

    success: bool
    sessions: list[dict] = []
    error: str | None = None


class SessionDetailResponse(BaseModel):
    """会话详情响应（包含消息）"""

    success: bool
    session: dict | None = None
    messages: list[dict] = []
    lastUsedModel: str | None = None
    lastUsedMode: str | None = None
    error: str | None = None


class MessagesResponse(BaseModel):
    """消息列表响应"""

    success: bool
    messages: list[dict] = []
    lastUsedModel: str | None = None
    lastUsedMode: str | None = None
    error: str | None = None


class CommonResponse(BaseModel):
    """通用响应"""

    success: bool
    message: str | None = None
    error: str | None = None


# ============== 会话 CRUD 路由 ==============


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    doc_id: str | None = Query(default=None, description="按文档 ID 过滤"),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """
    获取会话列表

    可选按 doc_id 过滤，返回按更新时间倒序排列的会话
    """
    try:
        service = SessionService(db)
        sessions = await service.get_sessions(doc_id=doc_id, limit=limit)
        return SessionListResponse(
            success=True,
            sessions=[s.to_dict() for s in sessions],
        )
    except Exception as e:
        return SessionListResponse(success=False, error=str(e))


@router.post("/sessions", response_model=SessionResponse)
async def create_session(
    request: CreateSessionRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    创建新会话
    """
    try:
        service = SessionService(db)
        session = await service.create_session(
            doc_id=request.docId,
            doc_name=request.docName,
            title=request.title or "新对话",
        )
        return SessionResponse(success=True, session=session.to_dict())
    except Exception as e:
        return SessionResponse(success=False, error=str(e))


@router.delete("/sessions", response_model=CommonResponse)
async def clear_all_sessions(
    db: AsyncSession = Depends(get_db),
):
    """
    清空所有会话及消息
    """
    try:
        service = SessionService(db)
        count = await service.clear_all_sessions()
        return CommonResponse(success=True, message=f"已清空所有会话，共删除 {count} 条消息")
    except Exception as e:
        return CommonResponse(success=False, error=str(e))


@router.get("/sessions/latest", response_model=SessionDetailResponse)
async def get_latest_session(
    doc_id: str | None = Query(default=None, description="按文档 ID 过滤"),
    db: AsyncSession = Depends(get_db),
):
    """
    获取最新的会话（含消息列表）

    用于 AIChatPane 初始加载时获取最近一次对话
    """
    try:
        service = SessionService(db)
        session = await service.get_latest_session(doc_id=doc_id)
        if not session:
            return SessionDetailResponse(success=True, session=None, messages=[])

        messages = await service.get_messages(session.id)
        last_settings = await service.get_last_used_settings(session.id)
        return SessionDetailResponse(
            success=True,
            session=session.to_dict(),
            messages=[m.to_dict() for m in messages],
            lastUsedModel=last_settings.get("model"),
            lastUsedMode=last_settings.get("mode"),
        )
    except Exception as e:
        return SessionDetailResponse(success=False, error=str(e))


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    获取会话详情（含消息列表）
    """
    try:
        service = SessionService(db)
        session = await service.get_session(session_id)
        if not session:
            return SessionDetailResponse(success=False, error="会话不存在")

        messages = await service.get_messages(session_id)
        last_settings = await service.get_last_used_settings(session_id)
        return SessionDetailResponse(
            success=True,
            session=session.to_dict(),
            messages=[m.to_dict() for m in messages],
            lastUsedModel=last_settings.get("model"),
            lastUsedMode=last_settings.get("mode"),
        )
    except Exception as e:
        return SessionDetailResponse(success=False, error=str(e))


@router.patch("/sessions/{session_id}", response_model=SessionResponse)
async def rename_session(
    session_id: int,
    request: RenameSessionRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    重命名会话
    """
    try:
        service = SessionService(db)
        session = await service.rename_session(session_id, request.title)
        if not session:
            return SessionResponse(success=False, error="会话不存在")
        return SessionResponse(success=True, session=session.to_dict())
    except Exception as e:
        return SessionResponse(success=False, error=str(e))


@router.delete("/sessions/{session_id}", response_model=CommonResponse)
async def delete_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    删除会话及其所有消息
    """
    try:
        service = SessionService(db)
        success = await service.delete_session(session_id)
        if not success:
            return CommonResponse(success=False, error="会话不存在")
        return CommonResponse(success=True, message="会话已删除")
    except Exception as e:
        return CommonResponse(success=False, error=str(e))


# ============== 会话消息路由 ==============


@router.get("/sessions/{session_id}/messages", response_model=MessagesResponse)
async def get_session_messages(
    session_id: int,
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    获取会话的消息列表
    """
    try:
        service = SessionService(db)
        messages = await service.get_messages(session_id, limit, offset)
        last_settings = await service.get_last_used_settings(session_id)
        return MessagesResponse(
            success=True,
            messages=[m.to_dict() for m in messages],
            lastUsedModel=last_settings.get("model"),
            lastUsedMode=last_settings.get("mode"),
        )
    except Exception as e:
        return MessagesResponse(success=False, error=str(e))


@router.post("/sessions/{session_id}/messages", response_model=CommonResponse)
async def add_message(
    session_id: int,
    request: AddMessageRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    向会话添加消息

    会自动更新会话的 preview、title、updated_at
    """
    try:
        service = SessionService(db)
        message = await service.add_message(
            session_id=session_id,
            role=request.role,
            content=request.content,
            document_json=request.documentJson,
            selection_context=request.selectionContext,
            content_parts=request.contentParts,
            model=request.model,
            mode=request.mode,
        )
        if not message:
            return CommonResponse(success=False, error="会话不存在")
        return CommonResponse(success=True, message="消息已保存")
    except Exception as e:
        return CommonResponse(success=False, error=str(e))


@router.delete("/sessions/{session_id}/messages", response_model=CommonResponse)
async def clear_session_messages(
    session_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    清空会话的所有消息（保留会话本身）
    """
    try:
        service = SessionService(db)
        success = await service.clear_session_messages(session_id)
        if not success:
            return CommonResponse(success=False, error="会话不存在")
        return CommonResponse(success=True, message="消息已清空")
    except Exception as e:
        return CommonResponse(success=False, error=str(e))
