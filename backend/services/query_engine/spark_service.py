"""
Spark SQL查询引擎服务实现 (占位符，后续实现)
"""

from typing import Dict, List, Any
import pandas as pd

from utils.logger import LoggerMixin
from .base import QueryEngineService
from utils.spark_utils import spark_utils


class SparkSQLService(QueryEngineService, LoggerMixin):
    """Spark SQL查询引擎服务实现"""

    def __init__(self):
        self.logger.info("Spark SQL查询引擎服务初始化完成")

    def execute_query(self, sql: str) -> list[dict]:
        """执行Spark SQL查询"""

        self.logger.debug(f"执行Spark SQL查询: {sql}")
        # 这里是占位符实现
        result = spark_utils.query_sql(sql)
        self.logger.debug(f"Spark SQL查询完成，返回 {len(result)} 行数据")
        return result


    def close(self):
        """关闭Spark连接"""
        spark_utils.close_spark_connect()