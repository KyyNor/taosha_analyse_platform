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

    def _initialize_sample_data(self):
        """初始化示例数据"""
        try:
            self.logger.info("开始初始化示例数据表结构")
            # 创建销售表
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS sales (
                    id INTEGER PRIMARY KEY,
                    product_name VARCHAR(100),
                    category VARCHAR(50),
                    price DECIMAL(10,2),
                    quantity INTEGER,
                    sale_date DATE,
                    customer_id INTEGER,
                    region VARCHAR(50)
                )
            """)

            self.logger.debug("创建销售表结构完成")
            # 创建客户表
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS customers (
                    customer_id INTEGER PRIMARY KEY,
                    customer_name VARCHAR(100),
                    age INTEGER,
                    gender VARCHAR(10),
                    city VARCHAR(50),
                    registration_date DATE
                )
            """)

            self.logger.debug("创建客户表结构完成")
            # 检查是否已有数据
            result = self.conn.execute("SELECT COUNT(*) FROM sales").fetchone()
            if result[0] == 0:
                self.logger.info("检测到销售表为空，开始插入示例数据")
                # 插入示例数据
                self._insert_sample_data()
            else:
                self.logger.info(f"销售表已存在数据，跳过初始化 (当前记录数: {result[0]})")

        except Exception as e:
            self.logger.error(f"初始化示例数据失败: {e}")

    def _insert_sample_data(self):
        """插入示例数据"""
        self.logger.info("开始插入销售数据")
        # 销售数据
        sales_data = [
            (1, '笔记本电脑', '电子产品', 5999.00, 2, '2024-01-15', 1, '北京'),
            (2, '手机', '电子产品', 3999.00, 1, '2024-01-16', 2, '上海'),
            (3, '键盘', '电子产品', 299.00, 3, '2024-01-17', 1, '北京'),
            (4, '显示器', '电子产品', 1999.00, 1, '2024-01-18', 3, '广州'),
            (5, '鼠标', '电子产品', 199.00, 2, '2024-01-19', 2, '上海'),
            (6, '平板电脑', '电子产品', 2999.00, 1, '2024-01-20', 4, '深圳'),
            (7, '耳机', '电子产品', 599.00, 1, '2024-01-21', 5, '杭州'),
            (8, '充电器', '电子产品', 99.00, 4, '2024-01-22', 3, '广州'),
        ]

        for sale in sales_data:
            self.conn.execute("""
                INSERT INTO sales VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, sale)

        self.logger.info(f"成功插入 {len(sales_data)} 条销售数据")

        # 客户数据
        customers_data = [
            (1, '张三', 28, '男', '北京', '2023-05-10'),
            (2, '李四', 35, '女', '上海', '2023-06-15'),
            (3, '王五', 42, '男', '广州', '2023-07-20'),
            (4, '赵六', 25, '女', '深圳', '2023-08-12'),
            (5, '钱七', 31, '男', '杭州', '2023-09-05'),
        ]

        for customer in customers_data:
            self.conn.execute("""
                INSERT INTO customers VALUES (?, ?, ?, ?, ?, ?)
            """, customer)

        self.logger.info(f"成功插入 {len(customers_data)} 条客户数据")
        self.logger.info("示例数据初始化完成")

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