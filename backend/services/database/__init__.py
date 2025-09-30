"""
数据库服务模块

提供统一的数据库服务接口，支持多种数据库类型：
- DuckDB: 嵌入式分析数据库
- Spark SQL: 分布式计算引擎
"""

from .base import DatabaseService, DatabaseServiceFactory
from .duckdb_service import DuckDBService
from .spark_service import SparkSQLService

# 全局数据库服务实例
_db_service = None


def get_database_service(service_type: str = None) -> DatabaseService:
    """
    获取数据库服务实例

    Args:
        service_type: 数据库服务类型，如果为None则从配置文件读取

    Returns:
        DatabaseService: 数据库服务实例
    """
    global _db_service

    if _db_service is None:
        # 如果没有指定类型，从配置文件读取
        if service_type is None:
            from utils.config import get_config
            config = get_config()
            service_type = config.get('database.service_type', 'duckdb')

        _db_service = DatabaseServiceFactory.create_service(service_type)

    return _db_service


def set_database_service(service: DatabaseService):
    """设置数据库服务实例"""
    global _db_service
    if _db_service:
        _db_service.close()
    _db_service = service


__all__ = [
    "DatabaseService",
    "DatabaseServiceFactory",
    "DuckDBService",
    "SparkSQLService",
    "get_database_service",
    "set_database_service"
]