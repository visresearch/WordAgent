"""
应用配置
"""

import os
import sys
from pathlib import Path

from pydantic_settings import BaseSettings


def get_data_dir() -> Path:
    """获取数据目录"""
    # 环境变量优先
    data_dir = os.environ.get("WENCE_DATA_DIR")
    if data_dir:
        return Path(data_dir)

    # 打包后的路径
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / "wence_data"

    # 开发环境
    return Path(__file__).parent.parent.parent / "wence_data"


def get_database_url() -> str:
    """获取数据库 URL"""
    try:
        data_dir = get_data_dir()
        data_dir.mkdir(parents=True, exist_ok=True, mode=0o755)
        db_path = data_dir / "wence_ai.db"
        # 确保数据库路径是绝对路径
        return f"sqlite+aiosqlite:///{db_path.absolute()}"
    except Exception:
        # 如果创建失败，使用临时目录
        import tempfile

        temp_dir = Path(tempfile.gettempdir()) / "wence_ai"
        temp_dir.mkdir(parents=True, exist_ok=True)
        db_path = temp_dir / "wence_ai.db"
        print(f"Warning: Using temp directory for database: {db_path}")
        return f"sqlite+aiosqlite:///{db_path.absolute()}"


def get_wence_data_dir() -> Path:
    """获取 wence_data 目录（用于配置文件等持久化数据）"""
    # 环境变量优先
    data_dir = os.environ.get("WENCE_DATA_DIR")
    if data_dir:
        return Path(data_dir)

    # 打包后的路径
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / "wence_data"

    # 开发环境
    return Path(__file__).parent.parent.parent / "wence_data"


def get_user_settings_file() -> Path:
    """获取用户设置文件路径（固定在 wence_data 目录）"""
    new_dir = get_wence_data_dir()
    new_dir.mkdir(parents=True, exist_ok=True, mode=0o755)
    return new_dir / "user_settings.json"


class Settings(BaseSettings):
    """应用配置"""

    # 基本信息
    APP_NAME: str = "WenCe AI Writing Assistant API"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"

    # 服务配置
    HOST: str = "127.0.0.1"  # 默认只监听本地，避免安全问题
    PORT: int = 3880
    DEBUG: bool = True

    # CORS 配置
    CORS_ORIGINS: list[str] = ["*"]

    # 文件处理配置
    MAX_TEXT_CHARS: int = 50000  # 注入到 LLM 上下文的文本最大字符数（约 25K tokens）

    # SQLite 数据库配置（嵌入式，无需安装）
    # 动态获取，支持打包后运行
    @property
    def database_url(self) -> str:
        return get_database_url()

    class Config:
        case_sensitive = True
        extra = "ignore"


# 全局配置实例
settings = Settings()
