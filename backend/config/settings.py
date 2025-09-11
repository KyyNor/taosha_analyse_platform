"""
淘沙分析平台 - 配置管理
"""

import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """应用配置"""
    
    # 应用信息
    app_name: str = "淘沙分析平台"
    app_version: str = "0.1.0"
    debug: bool = True
    
    # 数据库配置
    database_dir: Path = Path(__file__).parent.parent / "database"
    duckdb_path: str = str(database_dir / "taosha.duckdb")
    chromadb_path: str = str(database_dir / "chromadb")
    
    # 元数据配置
    metadata_file: str = str(database_dir / "metadata.json")
    glossary_file: str = str(database_dir / "glossary.json")
    
    # OpenAI配置
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    openai_base_url: Optional[str] = os.getenv("OPENAI_BASE_URL")
    openai_model: str = "Qwen/Qwen3-8B"
    
    # 缓存配置
    cache_ttl: int = 3600  # 1小时
    cache_size: int = 1000
    
    # 日志配置 (loguru)
    log_level: str = "INFO"  # 改为 INFO 减少日志输出
    log_rotation: str = "10 MB"  # 日志轮转大小
    log_retention: str = "7 days"  # 日志保留时间
    log_compression: str = "gz"  # 日志压缩格式
    
    class Config:
        env_prefix = "TAOSHA_"
        case_sensitive = False

# 全局配置实例
settings = Settings()

# 确保数据库目录存在
settings.database_dir.mkdir(parents=True, exist_ok=True)