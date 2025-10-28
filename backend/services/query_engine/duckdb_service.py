"""
DuckDB查询引擎服务实现
"""

from typing import Dict, List, Any
import pandas as pd
import duckdb

from utils.logger import LoggerMixin
from utils.config import settings
from .base import QueryEngineService


class DuckDBService(QueryEngineService, LoggerMixin):
    """DuckDB查询引擎服务实现"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or settings.duckdb_path
        self.conn = None
        self._connect()
        self.logger.info(f"DuckDB初始化完成，数据库路径: {self.db_path}")

    def _connect(self):
        """建立数据库连接"""
        try:
            self.conn = duckdb.connect(self.db_path)
            self.logger.debug(f"DuckDB连接成功: {self.db_path}")
        except Exception as e:
            self.logger.error(f"DuckDB连接失败: {e}")
            raise
        
    def execute_query(self, sql: str) -> list[dict]:
        """执行SQL查询"""
        try:
            self.logger.debug(f"执行SQL查询: {sql}")
            result = self.conn.execute(sql).fetchdf()
            result.to_dict('records')
            self.logger.debug(f"SQL查询完成，返回 {len(result)} 行数据")
            return result
        except Exception as e:
            self.logger.error(f"SQL查询执行失败: {e}")
            self.logger.error(f"失败的SQL语句: {sql}")
            raise

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.logger.info("DuckDB连接已关闭")