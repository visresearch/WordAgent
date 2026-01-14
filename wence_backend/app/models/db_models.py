"""
数据库 ORM 模型
"""

from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.db import Base


class Document(Base):
    """
    Word 文档记录
    使用文件的唯一标识（如文件路径 hash 或自定义 ID）来区分不同文档
    """

    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # 文档唯一标识符（前端传入，可以是文件路径、文件名 hash 等）
    doc_id = Column(String(128), unique=True, nullable=False, index=True)
    # 文档名称（用于显示）
    doc_name = Column(String(255), nullable=True)
    # 创建时间
    created_at = Column(DateTime, default=datetime.utcnow)
    # 最后更新时间
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联的聊天消息
    messages = relationship("ChatMessage", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Document(id={self.id}, doc_id='{self.doc_id}', doc_name='{self.doc_name}')>"


class ChatMessage(Base):
    """
    聊天消息记录
    """

    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # 关联的文档 ID
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    # 消息角色：user / assistant
    role = Column(String(20), nullable=False)
    # 消息内容（文本）
    content = Column(Text, nullable=False)
    # 文档 JSON 数据（AI 返回的结构化文档，可选）
    document_json = Column(JSON, nullable=True)
    # 选区上下文（用户选中的内容信息，可选）
    selection_context = Column(JSON, nullable=True)
    # 使用的模型
    model = Column(String(64), nullable=True)
    # 使用的模式（agent/ask）
    mode = Column(String(20), nullable=True)
    # 创建时间
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关联的文档
    document = relationship("Document", back_populates="messages")

    # 添加索引以加速按文档查询
    __table_args__ = (Index("idx_document_created", "document_id", "created_at"),)

    def __repr__(self):
        return f"<ChatMessage(id={self.id}, role='{self.role}', document_id={self.document_id})>"

    def to_dict(self):
        """转换为字典，用于 API 返回"""
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "documentJson": self.document_json,
            "selectionContext": self.selection_context,
            "model": self.model,
            "mode": self.mode,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }
