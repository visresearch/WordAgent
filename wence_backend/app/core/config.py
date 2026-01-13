"""
应用配置
"""

import os
import sys
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings


def get_data_dir() -> Path:
    """获取数据目录"""
    # 环境变量优先
    data_dir = os.environ.get("WENCE_DATA_DIR")
    if data_dir:
        return Path(data_dir)
    
    # 打包后的路径
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent / "data"
    
    # 开发环境
    return Path(__file__).parent.parent.parent / "data"


def get_database_url() -> str:
    """获取数据库 URL"""
    data_dir = get_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = data_dir / "wence_ai.db"
    return f"sqlite+aiosqlite:///{db_path}"


class Settings(BaseSettings):
    """应用配置"""
    
    # 基本信息
    APP_NAME: str = "WenCe AI Writing Assistant API"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    
    # 服务配置
    HOST: str = "0.0.0.0"
    PORT: int = 3880
    DEBUG: bool = True
    
    # CORS 配置
    CORS_ORIGINS: List[str] = ["*"]
    
    # AI 模型配置 - OpenAI
    OPENAI_DEFAULT_MODEL: str = "gpt-4o"
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = ""
    
    # 智谱
    ZHIPU_API_KEY: str = ""
    ZHIPU_BASE_URL: str = ""
    ZHIPU_DEFAULT_MODEL: str = "glm-4.7"

    # 千问
    QWEN_API_KEY: str = ""
    QWEN_BASE_URL: str = ""
    QWEN_DEFAULT_MODEL: str = "qwen-plus"

    # Ollama
    OLLAMA_API_KEY: str = "anystring"  # Ollama 不需要真正的 API Key，但必须提供一个字符串
    OLLAMA_BASE_URL: str = "http://localhost:11434/v1"
    OLLAMA_DEFAULT_MODEL: str = "qwen2.5:7b"
    
    # SQLite 数据库配置（嵌入式，无需安装）
    # 动态获取，支持打包后运行
    @property
    def database_url(self) -> str:
        return get_database_url()
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # 忽略 .env 中多余的字段


# 全局配置实例
settings = Settings()
