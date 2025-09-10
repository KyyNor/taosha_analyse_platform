"""
淘沙分析平台 - 配置管理
"""

import os
from pathlib import Path
from typing import Optional
from pydantic import BaseSettings

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
    openai_model: str = "gpt-3.5-turbo"
    
    # 缓存配置
    cache_ttl: int = 3600  # 1小时
    cache_size: int = 1000
    
    # 日志配置
    log_level: str = "DEBUG"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    class Config:
        env_prefix = "TAOSHA_"
        case_sensitive = False

# 全局配置实例
settings = Settings()

# 确保数据库目录存在
settings.database_dir.mkdir(parents=True, exist_ok=True)