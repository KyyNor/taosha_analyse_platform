"""
查询引擎服务抽象基类
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import pandas as pd


class QueryEngineService(ABC):
    """查询引擎服务抽象基类"""

    @abstractmethod
    def execute_query(self, sql: str) -> list[dict]:
        """执行SQL查询"""
        pass

    @abstractmethod
    def close(self):
        """关闭数据库连接"""
        pass


class QueryEngineFactory:
    """查询引擎服务工厂"""

    @staticmethod
    def create_service(service_type: str = "duckdb", **kwargs) -> QueryEngineService:
        """创建查询引擎服务实例"""
        if service_type.lower() == "duckdb":
            from .duckdb_service import DuckDBService
            return DuckDBService(**kwargs)
        elif service_type.lower() == "spark":
            from .spark_service import SparkSQLService
            return SparkSQLService(**kwargs)
        elif service_type.lower() == "empty":
            from .empty_engine_service import EmptyQueryEngineService
            return EmptyQueryEngineService(**kwargs)
        else:
            raise ValueError(f"不支持的查询引擎服务类型: {service_type}")

