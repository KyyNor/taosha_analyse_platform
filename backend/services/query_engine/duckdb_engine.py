"""
DuckDB查询引擎实现
用于开发和测试环境的轻量级查询引擎
"""
import asyncio
import time
from typing import Dict, List, Any, Optional
from pathlib import Path

import duckdb

from .base_engine import BaseQueryEngine, QueryResult
from utils.logger import get_logger
from utils.exceptions import QueryEngineException

logger = get_logger(__name__)


class DuckDBQueryEngine(BaseQueryEngine):
    """DuckDB查询引擎"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.db_path = config.get('path', ':memory:')
        self.connection = None
    
    async def connect(self) -> bool:
        """建立DuckDB连接"""
        try:
            # 如果是文件数据库，确保目录存在
            if self.db_path != ':memory:':
                db_path = Path(self.db_path)
                db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 创建连接
            self.connection = duckdb.connect(self.db_path)
            
            # 设置DuckDB配置
            await self._configure_duckdb()
            
            # 测试连接
            test_result = self.connection.execute("SELECT 1").fetchone()
            if test_result[0] != 1:
                raise QueryEngineException("DuckDB连接测试失败")
            
            self.is_connected = True
            logger.info(f"DuckDB连接成功: {self.db_path}")
            return True
            
        except Exception as e:
            logger.error(f"DuckDB连接失败: {e}")
            raise QueryEngineException(f"DuckDB连接失败: {e}")
    
    async def disconnect(self) -> bool:
        """断开DuckDB连接"""
        try:
            if self.connection:
                self.connection.close()
                self.connection = None
                self.is_connected = False
                logger.info("DuckDB连接已断开")
            return True
            
        except Exception as e:
            logger.error(f"DuckDB断开连接失败: {e}")
            return False
    
    async def execute_query(
        self,
        sql: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None
    ) -> QueryResult:
        """执行DuckDB查询"""
        if not self.is_connected:
            await self.connect()
        
        # 清理SQL
        sql = self._sanitize_sql(sql)
        
        try:
            start_time = time.time()
            
            # 执行查询
            if params:
                cursor = self.connection.execute(sql, params)
            else:
                cursor = self.connection.execute(sql)
            
            # 获取结果
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            logger.info(f"DuckDB查询执行成功，返回 {len(rows)} 行，耗时 {execution_time_ms}ms")
            
            return self._format_query_result(columns, rows, execution_time_ms, sql)
            
        except Exception as e:
            logger.error(f"DuckDB查询执行失败: {e}")
            raise QueryEngineException(f"查询执行失败: {e}")
    
    async def get_schema_info(self, table_name: Optional[str] = None) -> Dict[str, Any]:
        """获取DuckDB模式信息"""
        try:
            schema_info = {"tables": [], "columns": []}
            
            if table_name:
                # 获取指定表的列信息
                columns_sql = """
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns 
                    WHERE table_name = ?
                    ORDER BY ordinal_position
                """
                cursor = self.connection.execute(columns_sql, [table_name])
                columns = cursor.fetchall()
                
                for col in columns:
                    schema_info["columns"].append({
                        "column_name": col[0],
                        "data_type": col[1],
                        "is_nullable": col[2] == 'YES',
                        "default_value": col[3]
                    })
            else:
                # 获取所有表信息
                tables_sql = """
                    SELECT table_name, table_type
                    FROM information_schema.tables 
                    WHERE table_schema = 'main'
                    ORDER BY table_name
                """
                cursor = self.connection.execute(tables_sql)
                tables = cursor.fetchall()
                
                for table in tables:
                    schema_info["tables"].append({
                        "table_name": table[0],
                        "table_type": table[1]
                    })
            
            return schema_info
            
        except Exception as e:
            logger.error(f"获取DuckDB模式信息失败: {e}")
            return {"tables": [], "columns": []}
    
    async def validate_sql(self, sql: str) -> Dict[str, Any]:
        """验证DuckDB SQL语法"""
        try:
            sql = self._sanitize_sql(sql)
            
            # 使用EXPLAIN来验证SQL语法
            explain_sql = f"EXPLAIN {sql}"
            cursor = self.connection.execute(explain_sql)
            cursor.fetchall()  # 消费结果
            
            return {
                "valid": True,
                "errors": [],
                "warnings": []
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [str(e)],
                "warnings": []
            }
    
    async def _configure_duckdb(self):
        """配置DuckDB设置"""
        try:
            # 设置内存限制
            self.connection.execute("SET memory_limit='1GB'")
            
            # 设置线程数
            self.connection.execute("SET threads=4")
            
            # 启用进度条（开发环境）
            self.connection.execute("SET enable_progress_bar=true")
            
            logger.info("DuckDB配置完成")
            
        except Exception as e:
            logger.warning(f"DuckDB配置失败: {e}")
    
    async def create_sample_data(self):
        """创建示例数据（用于测试）"""
        try:
            # 创建用户表
            users_sql = """
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username VARCHAR(50) NOT NULL,
                    email VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT true
                )
            """
            self.connection.execute(users_sql)
            
            # 插入示例用户数据
            insert_users_sql = """
                INSERT OR IGNORE INTO users (user_id, username, email) VALUES
                (1, 'admin', 'admin@example.com'),
                (2, 'user1', 'user1@example.com'),
                (3, 'user2', 'user2@example.com')
            """
            self.connection.execute(insert_users_sql)
            
            # 创建订单表
            orders_sql = """
                CREATE TABLE IF NOT EXISTS orders (
                    order_id INTEGER PRIMARY KEY,
                    user_id INTEGER,
                    amount DECIMAL(10,2),
                    order_date DATE,
                    status VARCHAR(20) DEFAULT 'pending',
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """
            self.connection.execute(orders_sql)
            
            # 插入示例订单数据
            insert_orders_sql = """
                INSERT OR IGNORE INTO orders (order_id, user_id, amount, order_date, status) VALUES
                (101, 1, 299.99, '2024-10-01', 'completed'),
                (102, 2, 159.50, '2024-10-02', 'completed'),
                (103, 1, 89.99, '2024-10-03', 'pending'),
                (104, 3, 199.99, '2024-10-04', 'completed'),
                (105, 2, 349.99, '2024-10-05', 'shipped')
            """
            self.connection.execute(insert_orders_sql)
            
            # 创建产品表
            products_sql = """
                CREATE TABLE IF NOT EXISTS products (
                    product_id INTEGER PRIMARY KEY,
                    product_name VARCHAR(100) NOT NULL,
                    category VARCHAR(50),
                    price DECIMAL(10,2),
                    stock_quantity INTEGER DEFAULT 0
                )
            """
            self.connection.execute(products_sql)
            
            # 插入示例产品数据
            insert_products_sql = """
                INSERT OR IGNORE INTO products (product_id, product_name, category, price, stock_quantity) VALUES
                (1001, '笔记本电脑', '电子产品', 4999.00, 50),
                (1002, '无线鼠标', '配件', 129.00, 200),
                (1003, '机械键盘', '配件', 299.00, 80),
                (1004, '显示器', '电子产品', 1299.00, 30),
                (1005, '耳机', '配件', 199.00, 150)
            """
            self.connection.execute(insert_products_sql)
            
            logger.info("DuckDB示例数据创建完成")
            
        except Exception as e:
            logger.error(f"创建DuckDB示例数据失败: {e}")
    
    async def estimate_query_cost(self, sql: str) -> Dict[str, Any]:
        """估算DuckDB查询成本"""
        try:
            sql = self._sanitize_sql(sql)
            
            # 使用EXPLAIN ANALYZE来获取查询计划
            explain_sql = f"EXPLAIN ANALYZE {sql}"
            cursor = self.connection.execute(explain_sql)
            plan = cursor.fetchall()
            
            # 简单解析执行计划（实际实现会更复杂）
            estimated_rows = 0
            for row in plan:
                plan_line = str(row[0]) if row else ""
                if "rows=" in plan_line:
                    # 提取行数估计
                    try:
                        parts = plan_line.split("rows=")
                        if len(parts) > 1:
                            rows_part = parts[1].split()[0]
                            estimated_rows = max(estimated_rows, int(float(rows_part)))
                    except:
                        pass
            
            return {
                "estimated_rows": estimated_rows,
                "estimated_cost": estimated_rows * 0.1,  # 简单的成本估算
                "estimated_time_ms": estimated_rows // 100,  # 估算时间
                "query_plan": [str(row[0]) for row in plan]
            }
            
        except Exception as e:
            logger.warning(f"DuckDB查询成本估算失败: {e}")
            return {
                "estimated_rows": 0,
                "estimated_cost": 0.0,
                "estimated_time_ms": 0
            }
    
    def _get_supported_features(self) -> List[str]:
        """获取DuckDB支持的功能"""
        return [
            "basic_query",
            "schema_inspection", 
            "sql_validation",
            "connection_test",
            "query_plan",
            "cost_estimation",
            "sample_data_creation",
            "analytical_functions",
            "json_support",
            "parquet_support"
        ]