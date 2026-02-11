"""
数据库 ORM 模型

会话(Session)模型：每个聊天会话是一个独立的 Session，关联到具体文档。
消息(ChatMessage)模型：每条消息属于一个 Session。
"""

from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.db import Base


class Session(Base):
    """
    聊天会话记录
    每个会话是一轮独立的对话，可关联到某个文档
    """

    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # 关联的文档唯一标识符（可选，前端传入）
    doc_id = Column(String(128), nullable=True, index=True)
    # 文档名称（用于显示）
    doc_name = Column(String(255), nullable=True)
    # 会话标题（默认取第一条用户消息的前50字）
    title = Column(String(255), default="新对话")
    # 最后一条消息预览
    preview = Column(Text, nullable=True)
    # 创建时间
    created_at = Column(DateTime, default=datetime.utcnow)
    # 最后更新时间
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联的聊天消息
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Session(id={self.id}, title='{self.title}', doc_id='{self.doc_id}')>"

    def to_dict(self):
        """转换为字典，用于 API 返回"""
        return {
            "id": self.id,
            "docId": self.doc_id,
            "docName": self.doc_name,
            "title": self.title,
            "preview": self.preview,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }


class ChatMessage(Base):
    """
    聊天消息记录
    """

    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # 关联的会话 ID
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    # 消息角色：user / assistant
    role = Column(String(20), nullable=False)
    # 消息内容（文本）
    content = Column(Text, nullable=False)
    # 文档 JSON 数据（AI 返回的结构化文档，可选）
    document_json = Column(JSON, nullable=True)
    # 选区上下文（用户选中的内容信息，可选）
    selection_context = Column(JSON, nullable=True)
    # 结构化消息内容（包含 status 和 text 类型的部分）
    content_parts = Column(JSON, nullable=True)
    # 使用的模型
    model = Column(String(64), nullable=True)
    # 使用的模式（agent/ask）
    mode = Column(String(20), nullable=True)
    # 创建时间
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关联的会话
    session = relationship("Session", back_populates="messages")

    # 添加索引以加速按会话查询
    __table_args__ = (Index("idx_session_created", "session_id", "created_at"),)

    def __repr__(self):
        return f"<ChatMessage(id={self.id}, role='{self.role}', session_id={self.session_id})>"

    def to_dict(self):
        """转换为字典，用于 API 返回"""
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "documentJson": self.document_json,
            "selectionContext": self.selection_context,
            "contentParts": self.content_parts,
            "model": self.model,
            "mode": self.mode,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }
