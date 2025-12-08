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
            workers: int = self._config_data.get('app', {}).get('workers', True)

            # 数据库配置
            database_dir: Path = Path(self._config_data.get('database', {}).get('dir', './database'))
            duckdb_path: str = self._config_data.get('database', {}).get('duckdb_path', './database/taosha.duckdb')

            # 元数据配置
            taosha_db_type: str = self._config_data.get('taosha_db', {}).get('db_type', 'sqlite')

            # SQLite配置
            taosha_db_sqlite_path: str = self._config_data.get('taosha_db', {}).get('sqlite_path', './database/metadata.db')

            # MySQL配置
            taosha_db_mysql_host: str = self._config_data.get('taosha_db', {}).get('mysql', {}).get('host', 'localhost')
            taosha_db_mysql_port: int = self._config_data.get('taosha_db', {}).get('mysql', {}).get('port', 3306)
            taosha_db_mysql_database: str = self._config_data.get('taosha_db', {}).get('mysql', {}).get('database', 'taosha')
            taosha_db_mysql_user: str = self._config_data.get('taosha_db', {}).get('mysql', {}).get('user', 'root')
            taosha_db_mysql_password: str = self._config_data.get('taosha_db', {}).get('mysql', {}).get('password', '')
            taosha_db_mysql_charset: str = self._config_data.get('taosha_db', {}).get('mysql', {}).get('charset', 'utf8mb4')

            # 查询引擎配置
            query_engine_type: str = self._config_data.get('query_engine', {}).get('service_type', 'spark')
            query_engine_spark_jdbc_driver_class: str = self._config_data.get('query_engine', {}).get('spark', {}).get('jdbc_driver_class', 'org.apache.hive.jdbc.HiveDriver')
            query_engine_spark_jdbc_url: str = self._config_data.get('query_engine', {}).get('spark', {}).get('jdbc_url', 'jdbc:hive2://125.1.129.81:10000')
            query_engine_spark_user_name: str = self._config_data.get('query_engine', {}).get('spark', {}).get('user_name', 'bdspk')
            query_engine_spark_password: str = self._config_data.get('query_engine', {}).get('spark', {}).get('password', '')
            query_engine_jdbc_driver_jar_list: list[str] = self._config_data.get('query_engine', {}).get('jdbc_driver_jar', [])

            
            # OpenAI配置
            openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY") or self._config_data.get('openai', {}).get('api_key')
            openai_base_url: Optional[str] = os.getenv("OPENAI_BASE_URL") or self._config_data.get('openai', {}).get('base_url')
            openai_model: str = self._config_data.get('openai', {}).get('model', 'qwen/qwen3-8b:free')
            openai_temperature: float = self._config_data.get('openai', {}).get('temperature', 0.1)

            # Embedding配置
            embedding_type: str = self._config_data.get('embedding', {}).get('type', 'localai')  # localai 或 remote
            embedding_api_key: Optional[str] = os.getenv("EMBEDDING_API_KEY") or self._config_data.get('embedding', {}).get('api_key')
            embedding_base_url: Optional[str] = os.getenv("EMBEDDING_BASE_URL") or self._config_data.get('embedding', {}).get('base_url')
            embedding_model: str = self._config_data.get('embedding', {}).get('model', 'bge-large-zh-v1.5')
            embedding_dimensions: int = self._config_data.get('embedding', {}).get('dimensions', 1024)
            embedding_reranker_model: str = self._config_data.get('embedding', {}).get('reranker_model', 'bge-reranker-v2-m3')

            # 向量存储配置
            vector_store_collection_name: str = self._config_data.get('vector_store', {}).get('collection_name', 'taosha_knowledge')

            # Qdrant配置
            qdrant_url: Optional[str] = os.getenv("QDRANT_URL") or self._config_data.get('vector_store', {}).get('qdrant', {}).get('url')
            qdrant_api_key: Optional[str] = os.getenv("QDRANT_API_KEY") or self._config_data.get('vector_store', {}).get('qdrant', {}).get('api_key')
            qdrant_timeout: int = self._config_data.get('vector_store', {}).get('qdrant', {}).get('timeout', 30)

            # 日志配置
            log_level: str = self._config_data.get('logging', {}).get('level', 'INFO')
            log_rotation: str = self._config_data.get('logging', {}).get('rotation', '10 MB')
            log_retention: str = self._config_data.get('logging', {}).get('retention', '7 days')
            log_compression: str = self._config_data.get('logging', {}).get('compression', 'gz')

            # 跟踪配置
            tracing_type: Optional[str] = self._config_data.get('tracing', {}).get('tracing_type')
            phoenix_work_dir: Optional[str] = self._config_data.get('tracing', {}).get('phoenix_work_dir')
            phoenix_port: Optional[str] = self._config_data.get('tracing', {}).get('phoenix_port')
            langfuse_public_key: Optional[str] = os.getenv("LANGFUSE_PUBLIC_KEY") or self._config_data.get('tracing', {}).get('langfuse_public_key')
            langfuse_secret_key: Optional[str] = os.getenv("LANGFUSE_SECRET_KEY") or self._config_data.get('tracing', {}).get('langfuse_secret_key')
            langfuse_host: Optional[str] = os.getenv("LANGFUSE_HOST") or self._config_data.get('tracing', {}).get('langfuse_host')

            disk_cache_path: Optional[str] = self._config_data.get('disk_cache', {}).get('paht', './cache')

            # 元数据同步配置
            metadata_sync_enabled: bool = self._config_data.get('metadata_sync', {}).get('enabled', False)

            # 源数据库配置
            metadata_sync_source_db_host: str = self._config_data.get('metadata_sync', {}).get('source_db', {}).get('host', 'localhost')
            metadata_sync_source_db_port: int = self._config_data.get('metadata_sync', {}).get('source_db', {}).get('port', 3306)
            metadata_sync_source_db_database: str = self._config_data.get('metadata_sync', {}).get('source_db', {}).get('database', 'source_metadata')
            metadata_sync_source_db_user: str = self._config_data.get('metadata_sync', {}).get('source_db', {}).get('user', 'root')
            metadata_sync_source_db_password: str = self._config_data.get('metadata_sync', {}).get('source_db', {}).get('password', '')
            metadata_sync_source_db_charset: str = self._config_data.get('metadata_sync', {}).get('source_db', {}).get('charset', 'utf8mb4')
            metadata_sync_source_db_connection_timeout: int = self._config_data.get('metadata_sync', {}).get('source_db', {}).get('connection_timeout', 30)

            # 同步SQL
            metadata_sync_sql: str = self._config_data.get('metadata_sync', {}).get('sync_sql', '')

            # 同步选项
            metadata_sync_case_sensitive: bool = self._config_data.get('metadata_sync', {}).get('options', {}).get('case_sensitive', False)
            metadata_sync_max_retries: int = self._config_data.get('metadata_sync', {}).get('options', {}).get('max_retries', 3)
            metadata_sync_retry_delay: float = self._config_data.get('metadata_sync', {}).get('options', {}).get('retry_delay', 1.0)

            # FineReport配置
            fine_report_login_url: str = self._config_data.get('fine_report', {}).get('login_url', 'http://localhost:8075/webroot/decision/login')
            fine_report_user_name: Optional[str] = os.getenv("FINE_REPORT_USER_NAME") or self._config_data.get('fine_report', {}).get('user_name')
            fine_report_password: Optional[str] = os.getenv("FINE_REPORT_PASSWORD") or self._config_data.get('fine_report', {}).get('password')
            fine_report_designer_urls: list = self._config_data.get('fine_report', {}).get('designer_urls', [])
            fine_report_browser_headless: bool = self._config_data.get('fine_report', {}).get('browser', {}).get('headless', True)
            fine_report_browser_timeout: int = self._config_data.get('fine_report', {}).get('browser', {}).get('timeout', 30000)
            fine_report_browser_wait_timeout: int = self._config_data.get('fine_report', {}).get('browser', {}).get('wait_timeout', 5000)
            fine_report_browser_download_path: str = self._config_data.get('fine_report', {}).get('browser', {}).get('download_path', './downloads/fine_report')
            fine_report_browser_screenshot_path: str = self._config_data.get('fine_report', {}).get('browser', {}).get('screenshot_path', './downloads/screenshot')
            fine_report_download_timeout: int = self._config_data.get('fine_report', {}).get('download_timeout', 60000)

            # FineReport报表同步配置
            fine_report_sync_enabled: bool = self._config_data.get('fine_report_sync', {}).get('enabled', False)

            # FineReport源数据库配置
            fine_report_sync_source_db_host: str = self._config_data.get('fine_report_sync', {}).get('source_db', {}).get('host', 'localhost')
            fine_report_sync_source_db_port: int = self._config_data.get('fine_report_sync', {}).get('source_db', {}).get('port', 3306)
            fine_report_sync_source_db_database: str = self._config_data.get('fine_report_sync', {}).get('source_db', {}).get('database', 'fine_report_db')
            fine_report_sync_source_db_user: str = self._config_data.get('fine_report_sync', {}).get('source_db', {}).get('user', 'root')
            fine_report_sync_source_db_password: str = self._config_data.get('fine_report_sync', {}).get('source_db', {}).get('password', '')
            fine_report_sync_source_db_charset: str = self._config_data.get('fine_report_sync', {}).get('source_db', {}).get('charset', 'utf8mb4')
            fine_report_sync_source_db_connection_timeout: int = self._config_data.get('fine_report_sync', {}).get('source_db', {}).get('connection_timeout', 30)

            # FineReport同步SQL
            fine_report_sync_sql: str = self._config_data.get('fine_report_sync', {}).get('sync_sql', '')

            # FineReport同步选项
            fine_report_sync_case_sensitive: bool = self._config_data.get('fine_report_sync', {}).get('options', {}).get('case_sensitive', False)
            fine_report_sync_max_retries: int = self._config_data.get('fine_report_sync', {}).get('options', {}).get('max_retries', 3)
            fine_report_sync_retry_delay: float = self._config_data.get('fine_report_sync', {}).get('options', {}).get('retry_delay', 1.0)

            # DolphinScheduler配置
            dolphinscheduler_gateway_host: str = self._config_data.get('dolphinscheduler', {}).get('gateway', {}).get('host', '127.0.0.1')
            dolphinscheduler_gateway_api_port: int = self._config_data.get('dolphinscheduler', {}).get('gateway', {}).get('api_port', 25333)
            dolphinscheduler_gateway_user: str = self._config_data.get('dolphinscheduler', {}).get('gateway', {}).get('user', 'admin')
            dolphinscheduler_gateway_password: str = self._config_data.get('dolphinscheduler', {}).get('gateway', {}).get('password', 'dolphinscheduler123')
            dolphinscheduler_gateway_tenant: str = self._config_data.get('dolphinscheduler', {}).get('gateway', {}).get('tenant', 'default')
            dolphinscheduler_gateway_api_token: str = self._config_data.get('dolphinscheduler', {}).get('gateway', {}).get('api_token', 'default')
            dolphinscheduler_project_name: str = self._config_data.get('dolphinscheduler', {}).get('project_name', '淘沙分析平台')
            dolphinscheduler_project_code: str = self._config_data.get('dolphinscheduler', {}).get('project_code', '1')
            dolphinscheduler_callback_url: str = self._config_data.get('dolphinscheduler', {}).get('callback_url', 'http://127.0.0.1:50020/api/taosha/v1/fraudhunter/wide-table/indicator-runs/callback')
            dolphinscheduler_workflow_default_timezone: str = self._config_data.get('dolphinscheduler', {}).get('workflow', {}).get('default_timezone', 'Asia/Shanghai')
            dolphinscheduler_workflow_timeout: int = self._config_data.get('dolphinscheduler', {}).get('workflow', {}).get('timeout', 60)
            dolphinscheduler_workflow_params: dict = self._config_data.get('dolphinscheduler', {}).get('workflow', {}).get('params', {})
            dolphinscheduler_schedule_cron_expression: str = self._config_data.get('dolphinscheduler', {}).get('schedule', {}).get('cron_expression', '0 0 2 * * ?')
            dolphinscheduler_schedule_online_schedule: bool = self._config_data.get('dolphinscheduler', {}).get('schedule', {}).get('online_schedule', True)
            dolphinscheduler_task_table_check_timeout: int = self._config_data.get('dolphinscheduler', {}).get('task', {}).get('table_check', {}).get('timeout', 30)
            dolphinscheduler_task_table_check_fail_retry_times: int = self._config_data.get('dolphinscheduler', {}).get('task', {}).get('table_check', {}).get('fail_retry_times', 3)
            dolphinscheduler_task_table_check_fail_retry_interval: int = self._config_data.get('dolphinscheduler', {}).get('task', {}).get('table_check', {}).get('fail_retry_interval', 1)
            dolphinscheduler_task_sql_task_timeout: int = self._config_data.get('dolphinscheduler', {}).get('task', {}).get('sql_task', {}).get('timeout', 60)
            dolphinscheduler_task_sql_task_fail_retry_times: int = self._config_data.get('dolphinscheduler', {}).get('task', {}).get('sql_task', {}).get('fail_retry_times', 288)
            dolphinscheduler_task_sql_task_fail_retry_interval: int = self._config_data.get('dolphinscheduler', {}).get('task', {}).get('sql_task', {}).get('fail_retry_interval', 5)
            dolphinscheduler_task_sql_task_datasource_name: str = self._config_data.get('dolphinscheduler', {}).get('task', {}).get('sql_task', {}).get('datasource_name', 'spark_test')


            # FraudHunter配置
            fraudhunter_wide_table_storage_path: str = self._config_data.get('fraudhunter', {}).get('wide_table', {}).get('storage_path', './wide_tables')
            fraudhunter_wide_table_sync_check_interval: int = self._config_data.get('fraudhunter', {}).get('wide_table', {}).get('sync_check_interval', 300)
            fraudhunter_wide_table_sync_lookback_days: int = self._config_data.get('fraudhunter', {}).get('wide_table', {}).get('sync_lookback_days', 30)
            fraudhunter_wide_table_sync_scheduler_interval: int = self._config_data.get('fraudhunter', {}).get('wide_table', {}).get('sync_scheduler_interval', 600)
            fraudhunter_wide_table_source_table: str = self._config_data.get('fraudhunter', {}).get('wide_table', {}).get('source_table', 'hxb_dh_data_dwm.dwm_taosha_indicator_details')
            fraudhunter_wide_table_duckdb_config_memory_limit: str = self._config_data.get('fraudhunter', {}).get('wide_table', {}).get('duckdb_config', {}).get('memory_limit', '4GB')
            fraudhunter_wide_table_duckdb_config_threads: int = self._config_data.get('fraudhunter', {}).get('wide_table', {}).get('duckdb_config', {}).get('threads', 4)
            fraudhunter_scheduler_realtime_interval: int = self._config_data.get('fraudhunter', {}).get('scheduler', {}).get('realtime_interval', 300)
            fraudhunter_scheduler_offline_interval: int = self._config_data.get('fraudhunter', {}).get('scheduler', {}).get('offline_interval', 600)

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