"""
应用配置
"""

from typing import List
from pydantic_settings import BaseSettings


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
    
    # AI 模型配置
    DEFAULT_MODEL: str = "gpt-4"
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = ""
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# 全局配置实例
settings = Settings()
