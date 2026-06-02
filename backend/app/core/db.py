"""
数据库配置
使用 SQLite + SQLAlchemy 异步（嵌入式，无需用户安装）
"""

import json

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from app.core.config import settings

# 获取数据库 URL（动态，支持打包后运行）
DATABASE_URL = settings.database_url

# 创建异步引擎（SQLite 配置）
engine = create_async_engine(
    DATABASE_URL,
    echo=settings.DEBUG,  # 开发时打印 SQL
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


async def init_db():
    """
    初始化数据库，创建所有表并补齐历史版本缺失列。
    """
    async with engine.begin() as conn:

        def _check_and_create(connection):
            from sqlalchemy import inspect as sa_inspect

            inspector = sa_inspect(connection)
            tables = inspector.get_table_names()

            Base.metadata.create_all(connection)

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
                            print(f"✅ 已添加字段: chat_messages.{col_name}")
                    if "thinking" not in msg_columns:
                        connection.exec_driver_sql("ALTER TABLE chat_messages ADD COLUMN thinking TEXT")
                        print("✅ 已添加字段: chat_messages.thinking")
                    if "model" not in msg_columns:
                        connection.exec_driver_sql("ALTER TABLE chat_messages ADD COLUMN model VARCHAR(64)")
                        print("✅ 已添加字段: chat_messages.model")
                    if "provider" not in msg_columns:
                        connection.exec_driver_sql("ALTER TABLE chat_messages ADD COLUMN provider TEXT")
                        print("✅ 已添加字段: chat_messages.provider")
                    if "mode" not in msg_columns:
                        connection.exec_driver_sql("ALTER TABLE chat_messages ADD COLUMN mode VARCHAR(20)")
                        print("✅ 已添加字段: chat_messages.mode")
                except Exception as e:
                    print(f"⚠️ 添加 chat_messages 字段失败: {e}")

        await conn.run_sync(_check_and_create)


async def close_db():
    """
    关闭数据库连接
    """
    await engine.dispose()
