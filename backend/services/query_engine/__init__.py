"""
查询引擎模块

提供统一的查询引擎接口，支持多种OLAP引擎：
- DuckDB: 嵌入式分析数据库
- Spark SQL: 分布式计算引擎
- Empty: 轻量级测试引擎（无文件依赖）
"""

from .base import QueryEngineService, QueryEngineFactory
from .duckdb_service import DuckDBService
from .spark_service import SparkSQLService
from .empty_engine_service import EmptyQueryEngineService
from utils.logger import get_logger
from utils.config import settings

logger = get_logger(__name__)

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
        logger.debug("开始初始化查询引擎服务")
        # 如果没有指定类型，从配置文件读取
        if service_type is None:
            service_type = settings.query_engine_type
            logger.debug(f"从配置文件读取查询引擎类型: {service_type}")

        logger.info(f"创建查询引擎服务实例，类型: {service_type}")
        _engine_service = QueryEngineFactory.create_service(service_type)
        logger.info("查询引擎服务初始化完成")

    return _engine_service


def set_query_engine(service: QueryEngineService):
    """设置查询引擎实例"""
    global _engine_service
    logger.debug("设置查询引擎实例")
    if _engine_service:
        logger.info("关闭现有查询引擎实例")
        _engine_service.close()
    _engine_service = service
    logger.info("查询引擎实例设置完成")


# 向后兼容的别名
get_database_service = get_query_engine
set_database_service = set_query_engine


__all__ = [
    "QueryEngineService",
    "QueryEngineFactory",
    "DuckDBService",
    "SparkSQLService",
    "EmptyQueryEngineService",
    "get_query_engine",
    "set_query_engine",
    "get_database_service",  # 向后兼容
    "set_database_service"   # 向后兼容
]