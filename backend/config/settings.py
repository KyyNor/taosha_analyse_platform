"""
配置管理模块
"""
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from typing import List, Optional
from functools import lru_cache
import os
import yaml
from pathlib import Path
from loguru import logger


class Settings(BaseSettings):
    """应用配置"""
    
    # 基础配置
    DEBUG: bool = Field(default=True, env="DEBUG")
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    
    # 安全配置
    SECRET_KEY: str = Field(default="your-secret-key-here", env="SECRET_KEY")
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000", 
                "http://localhost:3001", "http://127.0.0.1:3001",
                "http://localhost:3002", "http://127.0.0.1:3002"],
        env="ALLOWED_ORIGINS"
    )
    ALLOWED_HOSTS: List[str] = Field(
        default=["localhost", "127.0.0.1"],
        env="ALLOWED_HOSTS"
    )
    
    # 日志配置
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FILE: Optional[str] = Field(default=None, env="LOG_FILE")
    
    # 数据库配置
    DATABASE_TYPE: str = Field(default="sqlite", env="DATABASE_TYPE")
    DATABASE_URL: Optional[str] = Field(default=None, env="DATABASE_URL")
    DATABASE_HOST: Optional[str] = Field(default=None, env="DATABASE_HOST")
    DATABASE_PORT: Optional[int] = Field(default=None, env="DATABASE_PORT")
    DATABASE_NAME: str = Field(default="taosha_metadata", env="DATABASE_NAME")
    DATABASE_USER: Optional[str] = Field(default=None, env="DATABASE_USER")
    DATABASE_PASSWORD: Optional[str] = Field(default=None, env="DATABASE_PASSWORD")
    DATABASE_PATH: str = Field(default="database/metadata.db", env="DATABASE_PATH")
    
    # 查询引擎配置
    QUERY_ENGINE_TYPE: str = Field(default="duckdb", env="QUERY_ENGINE_TYPE")
    QUERY_ENGINE_HOST: Optional[str] = Field(default=None, env="QUERY_ENGINE_HOST")
    QUERY_ENGINE_PORT: Optional[int] = Field(default=None, env="QUERY_ENGINE_PORT")
    QUERY_ENGINE_DATABASE: str = Field(default="business_data", env="QUERY_ENGINE_DATABASE")
    QUERY_ENGINE_USER: Optional[str] = Field(default=None, env="QUERY_ENGINE_USER")
    QUERY_ENGINE_PASSWORD: Optional[str] = Field(default=None, env="QUERY_ENGINE_PASSWORD")
    QUERY_ENGINE_PATH: str = Field(default="database/business.duckdb", env="QUERY_ENGINE_PATH")
    
    # LLM配置
    LLM_PROVIDER: str = Field(default="openai", env="LLM_PROVIDER")
    LLM_BASE_URL: Optional[str] = Field(default=None, env="LLM_BASE_URL")
    LLM_API_KEY: Optional[str] = Field(default=None, env="LLM_API_KEY")
    LLM_MODEL: str = Field(default="gpt-4-turbo", env="LLM_MODEL")
    LLM_TEMPERATURE: float = Field(default=0.1, env="LLM_TEMPERATURE")
    LLM_MAX_TOKENS: int = Field(default=4000, env="LLM_MAX_TOKENS")
    
    # 向量数据库配置
    VECTOR_DB_PATH: str = Field(default="database/vector_db", env="VECTOR_DB_PATH")
    VECTOR_DB_COLLECTION: str = Field(default="taosha_knowledge", env="VECTOR_DB_COLLECTION")
    
    # 查询配置
    QUERY_TIMEOUT: int = Field(default=30, env="QUERY_TIMEOUT")
    MAX_RETRY_COUNT: int = Field(default=3, env="MAX_RETRY_COUNT")
    MAX_RESULT_ROWS: int = Field(default=1000, env="MAX_RESULT_ROWS")
    
    # WebSocket配置
    WS_HEARTBEAT_INTERVAL: int = Field(default=30, env="WS_HEARTBEAT_INTERVAL")
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    @property
    def logger(self):
        """获取日志实例"""
        return logger
    
    def get_database_url(self) -> str:
        """获取数据库连接URL"""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        
        if self.DATABASE_TYPE == "sqlite":
            # 确保数据库目录存在
            db_path = Path(self.DATABASE_PATH)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            return f"sqlite:///{self.DATABASE_PATH}"
        elif self.DATABASE_TYPE == "mysql":
            return (
                f"mysql+aiomysql://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}"
                f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
            )
        else:
            raise ValueError(f"不支持的数据库类型: {self.DATABASE_TYPE}")
    
    def get_query_engine_config(self) -> dict:
        """获取查询引擎配置"""
        if self.QUERY_ENGINE_TYPE == "duckdb":
            # 确保数据库目录存在
            db_path = Path(self.QUERY_ENGINE_PATH)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            return {
                "type": "duckdb",
                "path": self.QUERY_ENGINE_PATH
            }
        elif self.QUERY_ENGINE_TYPE == "mysql":
            return {
                "type": "mysql",
                "host": self.QUERY_ENGINE_HOST,
                "port": self.QUERY_ENGINE_PORT,
                "database": self.QUERY_ENGINE_DATABASE,
                "user": self.QUERY_ENGINE_USER,
                "password": self.QUERY_ENGINE_PASSWORD
            }
        else:
            raise ValueError(f"不支持的查询引擎类型: {self.QUERY_ENGINE_TYPE}")


class ConfigManager:
    """配置管理器"""
    
    def __init__(self):
        self.config_path = Path("config")
        self.config_path.mkdir(exist_ok=True)
    
    def load_from_yaml(self, config_file: str) -> dict:
        """从YAML文件加载配置"""
        config_path = self.config_path / config_file
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        return {}
    
    def save_to_yaml(self, config_file: str, config_data: dict):
        """保存配置到YAML文件"""
        config_path = self.config_path / config_file
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)


@lru_cache()
def get_settings() -> Settings:
    """获取应用配置（单例模式）"""
    # 加载环境特定的配置文件
    env = os.getenv("ENVIRONMENT", "dev")
    config_manager = ConfigManager()
    
    # 尝试加载YAML配置
    yaml_config = config_manager.load_from_yaml(f"config.{env}.yaml")
    
    # 将YAML配置转换为环境变量格式
    for key, value in yaml_config.items():
        if isinstance(value, dict):
            for sub_key, sub_value in value.items():
                env_key = f"{key.upper()}_{sub_key.upper()}"
                if not os.getenv(env_key):
                    os.environ[env_key] = str(sub_value)
        else:
            env_key = key.upper()
            if not os.getenv(env_key):
                os.environ[env_key] = str(value)
    
    return Settings()