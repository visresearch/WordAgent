"""
会话管理服务
处理 Session CRUD 和 Session 下的消息操作
"""

from datetime import datetime

from sqlalchemy import delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import ChatMessage, Session


class SessionService:
    """会话管理服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ============== Session CRUD ==============

    async def create_session(
        self,
        title: str = "新对话",
    ) -> Session:
        """
        创建新会话

        Args:
            title: 会话标题

        Returns:
            Session 对象
        """
        session = Session(
            title=title,
        )
        self.db.add(session)
        await self.db.flush()
        return session

    async def get_session(self, session_id: int) -> Session | None:
        """获取单个会话"""
        result = await self.db.execute(select(Session).where(Session.id == session_id))
        return result.scalar_one_or_none()

    async def get_sessions(
        self,
        limit: int = 50,
    ) -> list[Session]:
        """
        获取会话列表

        Args:
            limit: 返回数量限制

        Returns:
            Session 列表，按更新时间倒序
        """
        query = select(Session).order_by(desc(Session.updated_at)).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_latest_session(self) -> Session | None:
        """
        获取最新的会话

        Returns:
            最新的 Session 或 None
        """
        query = select(Session).order_by(desc(Session.updated_at)).limit(1)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def rename_session(self, session_id: int, title: str) -> Session | None:
        """
        重命名会话

        Args:
            session_id: 会话 ID
            title: 新标题

        Returns:
            更新后的 Session 或 None（不存在时）
        """
        session = await self.get_session(session_id)
        if not session:
            return None
        session.title = title
        session.updated_at = datetime.utcnow()
        await self.db.flush()
        return session

    async def delete_session(self, session_id: int) -> bool:
        """
        删除会话及其所有消息

        Args:
            session_id: 会话 ID

        Returns:
            是否成功
        """
        session = await self.get_session(session_id)
        if not session:
            return False
        await self.db.delete(session)
        await self.db.flush()
        return True

    # ============== Message 操作 ==============

    async def get_messages(
        self,
        session_id: int,
        limit: int = 200,
        offset: int = 0,
    ) -> list[ChatMessage]:
        """
        获取会话的消息列表

        Args:
            session_id: 会话 ID
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            消息列表，按时间正序
        """
        result = await self.db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def add_message(
        self,
        session_id: int,
        role: str,
        content: str,
        document_json: dict | None = None,
        selection_context: list | dict | None = None,
        content_parts: list[dict] | None = None,
        thinking: str | None = None,
        model: str | None = None,
        mode: str | None = None,
        attached_files: list[dict] | None = None,
    ) -> ChatMessage | None:
        """
        向会话添加消息，并自动更新会话的 preview / title / updated_at

        Args:
            session_id: 会话 ID
            role: 消息角色（user/assistant）
            content: 消息内容
            其余同 ChatMessage 字段

        Returns:
            ChatMessage 对象，或 None（会话不存在时）
        """
        session = await self.get_session(session_id)
        if not session:
            return None

        message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            document_json=document_json,
            selection_context=selection_context,
            content_parts=content_parts,
            thinking=thinking,
            model=model,
            mode=mode,
            attached_files=attached_files,
        )
        self.db.add(message)

        # 更新会话预览为最后一条消息的前 100 字
        session.preview = content[:100] if content else ""
        session.updated_at = datetime.utcnow()

        # 如果是第一条用户消息且标题仍为默认值，自动设置标题
        if session.title == "新对话" and role == "user":
            session.title = content[:50] if len(content) > 50 else content

        await self.db.flush()
        return message

    async def get_last_used_settings(self, session_id: int) -> dict:
        """
        获取会话最后使用的 model 和 mode

        Args:
            session_id: 会话 ID

        Returns:
            包含 model 和 mode 的字典
        """
        result = await self.db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(desc(ChatMessage.created_at))
            .limit(1)
        )
        last_message = result.scalar_one_or_none()

        if not last_message:
            return {"model": None, "mode": None}

        return {"model": last_message.model, "mode": last_message.mode}

    async def clear_session_messages(self, session_id: int) -> bool:
        """
        清空会话的所有消息（保留会话本身）

        Args:
            session_id: 会话 ID

        Returns:
            是否成功
        """
        session = await self.get_session(session_id)
        if not session:
            return False

        await self.db.execute(delete(ChatMessage).where(ChatMessage.session_id == session_id))
        session.preview = None
        session.updated_at = datetime.utcnow()
        await self.db.flush()
        return True

    async def clear_all_sessions(self) -> int:
        """
        清空所有会话和消息

        Returns:
            删除的消息数量
        """
        # 统计消息数量
        count_result = await self.db.execute(select(func.count(ChatMessage.id)))
        count = count_result.scalar() or 0

        # 删除所有消息
        await self.db.execute(delete(ChatMessage))
        # 删除所有会话
        await self.db.execute(delete(Session))

        await self.db.flush()
        return count
