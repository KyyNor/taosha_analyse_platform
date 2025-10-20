"""
淘沙分析平台 - 配置管理工具类
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
import yaml
from pydantic_settings import BaseSettings


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器

        Args:
            config_path: 配置文件路径，默认为项目根目录下的config/config.yaml
        """
        if config_path is None:
            # 默认配置文件路径
            current_dir = Path(__file__).parent.parent
            config_path = current_dir / "config" / "config.yaml"

        self.config_path = Path(config_path)
        self._config_data = None
        self._settings = None

        # 确保配置文件存在
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")

        # 加载配置
        self._load_config()

        # 创建Pydantic设置实例
        self._create_settings()

    def _load_config(self) -> None:
        """加载YAML配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as file:
                self._config_data = yaml.safe_load(file)
        except Exception as e:
            raise RuntimeError(f"加载配置文件失败: {e}")

    def _create_settings(self) -> None:
        """创建Pydantic设置实例"""
        if not self._config_data:
            raise RuntimeError("配置数据未加载")

        class Settings(BaseSettings):
            """应用配置"""

            # 应用信息
            app_name: str = self._config_data.get('app', {}).get('name', '淘沙分析平台')
            app_version: str = self._config_data.get('app', {}).get('version', '0.1.0')
            debug: bool = self._config_data.get('app', {}).get('debug', True)

            # 数据库配置
            database_dir: Path = Path(self._config_data.get('database', {}).get('dir', './database'))
            duckdb_path: str = self._config_data.get('database', {}).get('duckdb_path', './database/taosha.duckdb')

            # 元数据配置
            taosha_db_db_type: str = self._config_data.get('taosha_db', {}).get('db_type', 'sqlite')

            # SQLite配置
            taosha_db_sqlite_path: str = self._config_data.get('taosha_db', {}).get('sqlite_path', './database/metadata.db')

            # MySQL配置
            taosha_db_mysql_host: str = self._config_data.get('taosha_db', {}).get('mysql', {}).get('host', 'localhost')
            taosha_db_mysql_port: int = self._config_data.get('taosha_db', {}).get('mysql', {}).get('port', 3306)
            taosha_db_mysql_database: str = self._config_data.get('taosha_db', {}).get('mysql', {}).get('database', 'taosha')
            taosha_db_mysql_user: str = self._config_data.get('taosha_db', {}).get('mysql', {}).get('user', 'root')
            taosha_db_mysql_password: str = self._config_data.get('taosha_db', {}).get('mysql', {}).get('password', '')
            taosha_db_mysql_charset: str = self._config_data.get('taosha_db', {}).get('mysql', {}).get('charset', 'utf8mb4')

            # OpenAI配置
            openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY") or self._config_data.get('openai', {}).get('api_key')
            openai_base_url: Optional[str] = os.getenv("OPENAI_BASE_URL") or self._config_data.get('openai', {}).get('base_url')
            openai_model: str = self._config_data.get('openai', {}).get('model', 'qwen/qwen3-8b:free')
            openai_temperature: float = self._config_data.get('openai', {}).get('temperature', 0.1)

            # Embedding配置
            embedding_type: str = self._config_data.get('embedding', {}).get('type', 'remote')  # remote 或 local
            embedding_api_key: Optional[str] = os.getenv("EMBEDDING_API_KEY") or self._config_data.get('embedding', {}).get('api_key')
            embedding_base_url: Optional[str] = os.getenv("EMBEDDING_BASE_URL") or self._config_data.get('embedding', {}).get('base_url')
            embedding_model: str = self._config_data.get('embedding', {}).get('model', 'text-embedding-3-small')
            embedding_dimensions: int = self._config_data.get('embedding', {}).get('dimensions', 1024)

            # 本地Embedding配置（统一到embedding配置下）
            embedding_model_path: Optional[str] = self._config_data.get('embedding', {}).get('model_path')
            embedding_device: str = self._config_data.get('embedding', {}).get('device', 'cpu')
            embedding_cache_size: int = self._config_data.get('embedding', {}).get('cache_size', 1000)

            # 向量存储配置
            vector_store_type: str = self._config_data.get('vector_store', {}).get('store_type', 'chromadb')
            vector_store_collection_name: str = self._config_data.get('vector_store', {}).get('collection_name', 'taosha_knowledge')
            vector_store_persist_dir: str = self._config_data.get('vector_store', {}).get('persist_dir', './database/chromadb')

            # 日志配置
            log_level: str = self._config_data.get('logging', {}).get('level', 'INFO')
            log_rotation: str = self._config_data.get('logging', {}).get('rotation', '10 MB')
            log_retention: str = self._config_data.get('logging', {}).get('retention', '7 days')
            log_compression: str = self._config_data.get('logging', {}).get('compression', 'gz')

            langfuse_public_key: Optional[str] = os.getenv("LANGFUSE_PUBLIC_KEY")
            langfuse_secret_key: Optional[str] = os.getenv("LANGFUSE_SECRET_KEY")
            langfuse_host: Optional[str] = os.getenv("LANGFUSE_HOST")

            class Config:
                env_prefix = self._config_data.get('env_prefix', 'TAOSHA_')
                case_sensitive = False
                env_file = ".env"
                env_file_encoding = "utf-8"

        self._settings = Settings()

        # 确保数据库目录存在
        self._settings.database_dir.mkdir(parents=True, exist_ok=True)

    def get_settings(self) -> BaseSettings:
        """获取设置实例"""
        if not self._settings:
            raise RuntimeError("配置未初始化")
        return self._settings

    def get_config_data(self) -> Dict[str, Any]:
        """获取原始配置数据"""
        if not self._config_data:
            raise RuntimeError("配置数据未加载")
        return self._config_data

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值，支持点号分隔的嵌套键"""
        if not self._config_data:
            raise RuntimeError("配置数据未加载")

        keys = key.split('.')
        value = self._config_data

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def reload(self) -> None:
        """重新加载配置"""
        self._load_config()
        self._create_settings()

    def update_config(self, key: str, value: Any) -> None:
        """更新配置值并保存到文件"""
        if not self._config_data:
            raise RuntimeError("配置数据未加载")

        keys = key.split('.')
        config = self._config_data

        # 导航到目标位置
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        # 设置值
        config[keys[-1]] = value

        # 保存到文件
        self._save_config()

        # 重新创建设置实例
        self._create_settings()

    def _save_config(self) -> None:
        """保存配置到文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as file:
                yaml.dump(self._config_data, file, default_flow_style=False,
                         ensure_ascii=False, allow_unicode=True)
        except Exception as e:
            raise RuntimeError(f"保存配置文件失败: {e}")


# 全局配置管理器实例
_config_manager = None


def get_config() -> ConfigManager:
    """获取全局配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_settings() -> BaseSettings:
    """获取全局设置实例"""
    return get_config().get_settings()


# 向后兼容的全局settings变量
settings = get_settings()

# 向后兼容的函数
def reload_config():
    """重新加载配置（向后兼容）"""
    get_config().reload()


def get_config_value(key: str, default: Any = None) -> Any:
    """获取配置值（向后兼容）"""
    return get_config().get(key, default)