"""
查询引擎模块

提供统一的查询引擎接口，支持多种OLAP引擎：
- DuckDB: 嵌入式分析数据库
- Spark SQL: 分布式计算引擎
"""

from .base import QueryEngineService, QueryEngineFactory
from .duckdb_service import DuckDBService
from .spark_service import SparkSQLService

# 全局查询引擎实例
_engine_service = None


def get_query_engine(service_type: str = None) -> QueryEngineService:
    """
    获取查询引擎实例

    Args:
        service_type: 查询引擎类型，如果为None则从配置文件读取

    Returns:
        QueryEngineService: 查询引擎实例
    """
    global _engine_service

    if _engine_service is None:
        # 如果没有指定类型，从配置文件读取
        if service_type is None:
            from utils.config import get_config
            config = get_config()
            service_type = config.get('query_engine.service_type', 'duckdb')

        _engine_service = QueryEngineFactory.create_service(service_type)

    return _engine_service


def set_query_engine(service: QueryEngineService):
    """设置查询引擎实例"""
    global _engine_service
    if _engine_service:
        _engine_service.close()
    _engine_service = service


# 向后兼容的别名
get_database_service = get_query_engine
set_database_service = set_query_engine


__all__ = [
    "QueryEngineService",
    "QueryEngineFactory",
    "DuckDBService",
    "SparkSQLService",
    "get_query_engine",
    "set_query_engine",
    "get_database_service",  # 向后兼容
    "set_database_service"   # 向后兼容
]