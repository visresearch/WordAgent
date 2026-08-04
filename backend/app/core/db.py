"""
数据库配置
使用 SQLite + SQLAlchemy 异步（嵌入式，无需用户安装）
"""

import json

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# 获取数据库 URL（动态，支持打包后运行）
DATABASE_URL = settings.database_url

# 创建异步引擎（SQLite 配置）
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # SQL 日志统一交给 logging 管理，避免 SQLAlchemy echo 重复输出
    pool_pre_ping=True,  # 检查连接是否有效
    pool_recycle=3600,  # 1小时后回收连接
    json_serializer=lambda obj: json.dumps(obj, ensure_ascii=False),
    json_deserializer=json.loads,
    # SQLite aiosqlite 不需要 check_same_thread
)

# 创建异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False, autocommit=False, autoflush=False
)

# 声明基类
Base = declarative_base()


async def get_db():
    """
    获取数据库会话的依赖注入函数
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def _initialize_schema(connection) -> None:
    """创建当前表结构，并为旧业务会话补充对外 UUID。"""
    from sqlalchemy import inspect as sa_inspect

    inspector = sa_inspect(connection)
    tables = inspector.get_table_names()

    Base.metadata.create_all(connection)

    if "sessions" in tables:
        from app.services.utils import generate_uuid7

        session_columns = {col["name"] for col in sa_inspect(connection).get_columns("sessions")}
        if "session_uuid" not in session_columns:
            connection.exec_driver_sql("ALTER TABLE sessions ADD COLUMN session_uuid VARCHAR(36)")
            logger.info("已添加字段: sessions.session_uuid")

        missing_ids = connection.exec_driver_sql(
            "SELECT id FROM sessions WHERE session_uuid IS NULL OR session_uuid = ''"
        ).fetchall()
        for row in missing_ids:
            connection.exec_driver_sql(
                "UPDATE sessions SET session_uuid = ? WHERE id = ?",
                (generate_uuid7(), row[0]),
            )
        connection.exec_driver_sql("CREATE UNIQUE INDEX IF NOT EXISTS idx_sessions_uuid ON sessions(session_uuid)")
        if missing_ids:
            logger.info("已为 %s 个历史会话生成 UUID", len(missing_ids))

    if "chat_messages" in tables:
        try:
            msg_columns = {col["name"] for col in sa_inspect(connection).get_columns("chat_messages")}
            json_columns = {
                "selection_context",
                "content_parts",
                "attached_files",
                "tool_json",
            }
            for col_name in json_columns:
                if col_name not in msg_columns:
                    connection.exec_driver_sql(f"ALTER TABLE chat_messages ADD COLUMN {col_name} JSON")
                    logger.info("已添加字段: chat_messages.%s", col_name)
            if "thinking" not in msg_columns:
                connection.exec_driver_sql("ALTER TABLE chat_messages ADD COLUMN thinking TEXT")
                logger.info("已添加字段: chat_messages.thinking")
            if "model" not in msg_columns:
                connection.exec_driver_sql("ALTER TABLE chat_messages ADD COLUMN model VARCHAR(64)")
                logger.info("已添加字段: chat_messages.model")
            if "provider" not in msg_columns:
                connection.exec_driver_sql("ALTER TABLE chat_messages ADD COLUMN provider TEXT")
                logger.info("已添加字段: chat_messages.provider")
            if "mode" not in msg_columns:
                connection.exec_driver_sql("ALTER TABLE chat_messages ADD COLUMN mode VARCHAR(20)")
                logger.info("已添加字段: chat_messages.mode")
        except Exception as e:
            logger.warning("添加 chat_messages 字段失败: %s", e)


async def init_db():
    """初始化数据库，创建所有表并补齐历史版本缺失列。"""
    async with engine.begin() as conn:
        await conn.run_sync(_initialize_schema)


async def close_db():
    """
    关闭数据库连接
    """
    await engine.dispose()
