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
            # 如果旧的 documents 表存在但新的 sessions 表不存在，需要迁移
            if "documents" in tables and "sessions" not in tables:
                print("🔄 检测到旧表结构，正在迁移到 Session 模式...")
                Base.metadata.drop_all(connection)
                print("   ✅ 旧表已清除")
            Base.metadata.create_all(connection)

        await conn.run_sync(_check_and_create)


async def close_db():
    """
    关闭数据库连接
    """
    await engine.dispose()
