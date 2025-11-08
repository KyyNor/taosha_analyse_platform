"""
Empty查询引擎服务实现
专门用于测试和开发环境，避免多worker场景下的文件冲突问题
"""

from typing import Dict, List, Any, Optional
import re
import pandas as pd
from utils.logger import LoggerMixin

try:
    from .base import QueryEngineService
except ImportError:
    # 如果无法使用相对导入，使用绝对导入
    from base import QueryEngineService


class EmptyQueryEngineService(QueryEngineService, LoggerMixin):
    """Empty查询引擎服务实现"""

    def __init__(self):
        self.conn = None
        self._mock_tables = {
            'users': [
                {'id': 1, 'name': 'Alice', 'age': 25, 'city': 'Beijing'},
                {'id': 2, 'name': 'Bob', 'age': 30, 'city': 'Shanghai'},
                {'id': 3, 'name': 'Charlie', 'age': 35, 'city': 'Guangzhou'}
            ],
            'products': [
                {'id': 1, 'name': 'Laptop', 'price': 5999, 'category': 'Electronics'},
                {'id': 2, 'name': 'Phone', 'price': 3999, 'category': 'Electronics'},
                {'id': 3, 'name': 'Book', 'price': 99, 'category': 'Education'}
            ]
        }
        self.logger.info("EmptyQueryEngine初始化完成")

    def execute_query(self, sql: str) -> list[dict]:
        """
        执行SQL查询（模拟实现）

        Args:
            sql: SQL查询语句

        Returns:
            查询结果列表
        """
        try:
            self.logger.debug(f"执行SQL查询: {sql}")

            # 去除前后空格并转为小写进行分析
            sql_clean = sql.strip().lower()

            # 处理SELECT查询
            if sql_clean.startswith('select'):
                return self._handle_select_query(sql_clean)

            # 处理INSERT查询
            elif sql_clean.startswith('insert'):
                self.logger.debug("INSERT操作 - 模拟成功")
                return [{"affected_rows": 1}]

            # 处理UPDATE查询
            elif sql_clean.startswith('update'):
                self.logger.debug("UPDATE操作 - 模拟成功")
                return [{"affected_rows": 1}]

            # 处理DELETE查询
            elif sql_clean.startswith('delete'):
                self.logger.debug("DELETE操作 - 模拟成功")
                return [{"affected_rows": 1}]

            # 处理CREATE TABLE
            elif sql_clean.startswith('create table'):
                self.logger.debug("CREATE TABLE操作 - 模拟成功")
                return [{"success": True}]

            # 处理DROP TABLE
            elif sql_clean.startswith('drop table'):
                self.logger.debug("DROP TABLE操作 - 模拟成功")
                return [{"success": True}]

            else:
                self.logger.warning(f"不支持的SQL类型: {sql}")
                return []

        except Exception as e:
            self.logger.error(f"SQL查询执行失败: {e}")
            self.logger.error(f"失败的SQL语句: {sql}")
            raise

    def _handle_select_query(self, sql: str) -> list[dict]:
        """处理SELECT查询"""
        try:
            # 简单解析FROM子句获取表名
            from_match = re.search(r'from\s+(\w+)', sql, re.IGNORECASE)
            if not from_match:
                # 如果没有FROM子句，返回空结果
                return []

            table_name = from_match.group(1)

            # 如果表名存在于mock数据中
            if table_name in self._mock_tables:
                mock_data = self._mock_tables[table_name]

                # 检查是否有WHERE条件（简单模拟）
                if 'where' in sql:
                    # 简单的WHERE条件模拟（仅支持相等条件）
                    where_match = re.search(r'where\s+(\w+)\s*=\s*[\'"]?([^\'"\s]+)[\'"]?', sql, re.IGNORECASE)
                    if where_match:
                        column = where_match.group(1)
                        value = where_match.group(2)

                        # 尝试将值转换为数字
                        try:
                            if value.isdigit():
                                value = int(value)
                            elif '.' in value:
                                value = float(value)
                        except:
                            pass

                        # 过滤数据
                        mock_data = [row for row in mock_data if str(row.get(column, '')) == str(value)]

                # 检查是否有LIMIT子句
                if 'limit' in sql:
                    limit_match = re.search(r'limit\s+(\d+)', sql, re.IGNORECASE)
                    if limit_match:
                        limit = int(limit_match.group(1))
                        mock_data = mock_data[:limit]

                self.logger.debug(f"SELECT查询完成，返回 {len(mock_data)} 行数据")
                return mock_data
            else:
                self.logger.debug(f"表 '{table_name}' 不存在，返回空结果")
                return []

        except Exception as e:
            self.logger.error(f"SELECT查询处理失败: {e}")
            return []

    def get_tables(self) -> list[str]:
        """
        获取所有表名

        Returns:
            表名列表
        """
        tables = list(self._mock_tables.keys())
        self.logger.debug(f"获取表列表: {tables}")
        return tables

    def get_table_schema(self, table_name: str) -> dict:
        """
        获取表结构信息

        Args:
            table_name: 表名

        Returns:
            表结构信息
        """
        if table_name in self._mock_tables:
            # 分析mock数据获取列信息
            sample_row = self._mock_tables[table_name][0] if self._mock_tables[table_name] else {}
            schema = {}
            for column, value in sample_row.items():
                if isinstance(value, int):
                    column_type = 'INTEGER'
                elif isinstance(value, float):
                    column_type = 'FLOAT'
                else:
                    column_type = 'VARCHAR'
                schema[column] = column_type

            self.logger.debug(f"获取表 '{table_name}' 的结构: {schema}")
            return {
                'table_name': table_name,
                'columns': schema
            }
        else:
            self.logger.warning(f"表 '{table_name}' 不存在")
            return {}

    def add_mock_data(self, table_name: str, data: list[dict]):
        """
        添加模拟数据

        Args:
            table_name: 表名
            data: 数据列表
        """
        if table_name not in self._mock_tables:
            self._mock_tables[table_name] = []
        self._mock_tables[table_name].extend(data)
        self.logger.debug(f"为表 '{table_name}' 添加了 {len(data)} 条模拟数据")

    def clear_mock_data(self, table_name: str = None):
        """
        清除模拟数据

        Args:
            table_name: 表名，如果为None则清除所有表数据
        """
        if table_name:
            if table_name in self._mock_tables:
                self._mock_tables[table_name] = []
                self.logger.debug(f"清除表 '{table_name}' 的数据")
        else:
            for table in self._mock_tables:
                self._mock_tables[table] = []
            self.logger.debug("清除所有表的模拟数据")

    def close(self):
        """关闭数据库连接（模拟实现）"""
        self.logger.info("EmptyQueryEngine连接已关闭")

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()