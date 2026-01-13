"""
聊天历史记录服务
"""

from typing import List, Optional
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import Document, ChatMessage


class ChatHistoryService:
    """聊天历史记录服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_or_create_document(self, doc_id: str, doc_name: Optional[str] = None) -> Document:
        """
        获取或创建文档记录
        
        Args:
            doc_id: 文档唯一标识符
            doc_name: 文档名称（可选）
        
        Returns:
            Document 对象
        """
        # 查询已存在的文档
        result = await self.db.execute(
            select(Document).where(Document.doc_id == doc_id)
        )
        document = result.scalar_one_or_none()
        
        if document:
            # 更新文档名称（如果提供了新名称）
            if doc_name and document.doc_name != doc_name:
                document.doc_name = doc_name
                await self.db.flush()
            return document
        
        # 创建新文档
        document = Document(doc_id=doc_id, doc_name=doc_name)
        self.db.add(document)
        await self.db.flush()
        return document
    
    async def add_message(
        self,
        doc_id: str,
        role: str,
        content: str,
        document_json: Optional[dict] = None,
        selection_context: Optional[dict] = None,
        model: Optional[str] = None,
        mode: Optional[str] = None,
        doc_name: Optional[str] = None
    ) -> ChatMessage:
        """
        添加聊天消息
        
        Args:
            doc_id: 文档唯一标识符
            role: 消息角色（user/assistant）
            content: 消息内容
            document_json: AI 生成的文档 JSON
            selection_context: 选区上下文
            model: 使用的模型
            mode: 使用的模式
            doc_name: 文档名称
        
        Returns:
            ChatMessage 对象
        """
        # 获取或创建文档
        document = await self.get_or_create_document(doc_id, doc_name)
        
        # 创建消息
        message = ChatMessage(
            document_id=document.id,
            role=role,
            content=content,
            document_json=document_json,
            selection_context=selection_context,
            model=model,
            mode=mode
        )
        self.db.add(message)
        await self.db.flush()
        return message
    
    async def get_history(
        self,
        doc_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[dict]:
        """
        获取指定文档的聊天历史
        
        Args:
            doc_id: 文档唯一标识符
            limit: 返回的消息数量限制
            offset: 偏移量
        
        Returns:
            消息列表（字典格式）
        """
        # 先查找文档
        doc_result = await self.db.execute(
            select(Document).where(Document.doc_id == doc_id)
        )
        document = doc_result.scalar_one_or_none()
        
        if not document:
            return []
        
        # 查询消息，按时间正序排列
        result = await self.db.execute(
            select(ChatMessage)
            .where(ChatMessage.document_id == document.id)
            .order_by(ChatMessage.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        messages = result.scalars().all()
        
        return [msg.to_dict() for msg in messages]
    
    async def get_last_used_settings(self, doc_id: str) -> dict:
        """
        获取指定文档最后使用的 model 和 mode
        
        Args:
            doc_id: 文档唯一标识符
        
        Returns:
            包含 model 和 mode 的字典
        """
        # 先查找文档
        doc_result = await self.db.execute(
            select(Document).where(Document.doc_id == doc_id)
        )
        document = doc_result.scalar_one_or_none()
        
        if not document:
            return {'model': None, 'mode': None}
        
        # 查询最后一条消息，获取其 model 和 mode
        result = await self.db.execute(
            select(ChatMessage)
            .where(ChatMessage.document_id == document.id)
            .order_by(desc(ChatMessage.created_at))
            .limit(1)
        )
        last_message = result.scalar_one_or_none()
        
        if not last_message:
            return {'model': None, 'mode': None}
        
        return {
            'model': last_message.model,
            'mode': last_message.mode
        }
    
    async def clear_history(self, doc_id: str) -> bool:
        """
        清空指定文档的聊天历史
        
        Args:
            doc_id: 文档唯一标识符
        
        Returns:
            是否成功
        """
        # 查找文档
        doc_result = await self.db.execute(
            select(Document).where(Document.doc_id == doc_id)
        )
        document = doc_result.scalar_one_or_none()
        
        if not document:
            return False
        
        # 删除该文档的所有消息
        from sqlalchemy import delete
        await self.db.execute(
            delete(ChatMessage).where(ChatMessage.document_id == document.id)
        )
        await self.db.flush()
        return True
    
    async def clear_all_history(self) -> int:
        """
        清空所有文档的聊天历史
        
        Returns:
            删除的消息数量
        """
        from sqlalchemy import delete, func
        
        # 统计消息数量
        count_result = await self.db.execute(
            select(func.count(ChatMessage.id))
        )
        count = count_result.scalar() or 0
        
        # 删除所有消息
        await self.db.execute(delete(ChatMessage))
        
        # 删除所有文档记录
        await self.db.execute(delete(Document))
        
        await self.db.flush()
        return count

    async def get_all_documents(self, limit: int = 100) -> List[dict]:
        """
        获取所有有聊天记录的文档列表
        
        Args:
            limit: 返回数量限制
        
        Returns:
            文档列表
        """
        result = await self.db.execute(
            select(Document)
            .order_by(desc(Document.updated_at))
            .limit(limit)
        )
        documents = result.scalars().all()

        return [
            {
                "docId": doc.doc_id,
                "docName": doc.doc_name,
                "createdAt": doc.created_at.isoformat() if doc.created_at else None,
                "updatedAt": doc.updated_at.isoformat() if doc.updated_at else None
            }
            for doc in documents
        ]
