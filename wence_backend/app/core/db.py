"""
数据库配置
使用 SQLite + SQLAlchemy 异步（嵌入式，无需用户安装）
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
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
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
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
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """
    关闭数据库连接
    """
    await engine.dispose()
