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
        self._initialize_sample_data()
        self.logger.info(f"DuckDB初始化完成，数据库路径: {self.db_path}")

    def _connect(self):
        """建立数据库连接"""
        try:
            self.conn = duckdb.connect(self.db_path)
            self.logger.debug(f"DuckDB连接成功: {self.db_path}")
        except Exception as e:
            self.logger.error(f"DuckDB连接失败: {e}")
            raise
        
        
    def execute_query(self, sql: str) -> pd.DataFrame:
        """执行SQL查询"""
        try:
            self.logger.debug(f"执行SQL查询: {sql}")
            result = self.conn.execute(sql).fetchdf()
            self.logger.debug(f"SQL查询完成，返回 {len(result)} 行数据")
            return result
        except Exception as e:
            self.logger.error(f"SQL查询执行失败: {e}")
            self.logger.error(f"失败的SQL语句: {sql}")
            raise

    def get_tables(self) -> List[str]:
        """获取所有表名"""
        try:
            self.logger.debug("开始获取数据库表列表")
            result = self.conn.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'main'
            """).fetchall()
            tables = [row[0] for row in result]
            self.logger.debug(f"获取到表列表: {tables}")
            return tables
        except Exception as e:
            self.logger.error(f"获取表列表失败: {e}")
            return []

    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """获取表结构"""
        try:
            self.logger.debug(f"开始获取表 {table_name} 的结构信息")
            # 获取列信息
            columns_result = self.conn.execute(f"""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = '{table_name}'
                ORDER BY ordinal_position
            """).fetchall()

            # 获取行数
            count_result = self.conn.execute(f"""
                SELECT COUNT(*) FROM {table_name}
            """).fetchone()

            schema = {
                'table_name': table_name,
                'row_count': count_result[0],
                'columns': [
                    {
                        'name': col[0],
                        'type': col[1],
                        'nullable': col[2] == 'YES'
                    }
                    for col in columns_result
                ]
            }

            self.logger.debug(f"表 {table_name} 结构信息: {schema}")
            return schema

        except Exception as e:
            self.logger.error(f"获取表 {table_name} 结构失败: {e}")
            return {'error': str(e)}

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.logger.info("DuckDB连接已关闭")