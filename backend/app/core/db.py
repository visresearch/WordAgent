"""
数据库配置
使用 SQLite + SQLAlchemy 异步（嵌入式，无需用户安装）
"""

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
    初始化数据库，创建所有表
    如果检测到旧表结构（无 sessions 表），则自动迁移
    """
    async with engine.begin() as conn:

        def _check_and_create(connection):
            from sqlalchemy import inspect as sa_inspect

            inspector = sa_inspect(connection)
            tables = inspector.get_table_names()

            Base.metadata.create_all(connection)

            # 清理历史遗留 documents 表
            if "documents" in tables:
                try:
                    connection.exec_driver_sql("DROP TABLE IF EXISTS documents")
                    print("🧹 已移除遗留表: documents")
                except Exception as e:
                    print(f"⚠️ 移除遗留表 documents 失败: {e}")

            # 清理 sessions 表中的历史字段（若存在）
            try:
                columns = {col["name"] for col in sa_inspect(connection).get_columns("sessions")}
                for legacy_col in ("doc_id", "doc_name"):
                    if legacy_col in columns:
                        try:
                            connection.exec_driver_sql(f"ALTER TABLE sessions DROP COLUMN {legacy_col}")
                            print(f"🧹 已移除历史字段: sessions.{legacy_col}")
                        except Exception as drop_err:
                            print(f"⚠️ 移除字段 sessions.{legacy_col} 失败: {drop_err}")
            except Exception as e:
                print(f"⚠️ 清理 sessions 历史字段失败: {e}")

            # 迁移：为 chat_messages 添加 thinking 列
            if "chat_messages" in tables:
                try:
                    msg_columns = {col["name"] for col in sa_inspect(connection).get_columns("chat_messages")}
                    if "thinking" not in msg_columns:
                        connection.exec_driver_sql("ALTER TABLE chat_messages ADD COLUMN thinking TEXT")
                        print("✅ 已添加字段: chat_messages.thinking")
                except Exception as e:
                    print(f"⚠️ 添加 chat_messages.thinking 字段失败: {e}")

        await conn.run_sync(_check_and_create)


async def close_db():
    """
    关闭数据库连接
    """
    await engine.dispose()
