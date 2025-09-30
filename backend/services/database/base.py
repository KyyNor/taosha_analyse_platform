"""
数据库服务抽象基类
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import pandas as pd


class DatabaseService(ABC):
    """数据库服务抽象基类"""

    @abstractmethod
    def execute_query(self, sql: str) -> pd.DataFrame:
        """执行SQL查询"""
        pass

    @abstractmethod
    def get_tables(self) -> List[str]:
        """获取所有表名"""
        pass

    @abstractmethod
    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """获取表结构"""
        pass

    @abstractmethod
    def close(self):
        """关闭数据库连接"""
        pass


class DatabaseServiceFactory:
    """数据库服务工厂"""

    @staticmethod
    def create_service(service_type: str = "duckdb", **kwargs) -> DatabaseService:
        """创建数据库服务实例"""
        if service_type.lower() == "duckdb":
            from .duckdb_service import DuckDBService
            return DuckDBService(**kwargs)
        elif service_type.lower() == "spark":
            from .spark_service import SparkSQLService
            return SparkSQLService(**kwargs)
        else:
            raise ValueError(f"不支持的数据库服务类型: {service_type}")