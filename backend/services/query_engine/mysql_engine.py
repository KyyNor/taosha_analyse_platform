"""
MySQL查询引擎实现
用于生产环境的MySQL数据库查询引擎
"""
import asyncio
import time
from typing import Dict, List, Any, Optional

import aiomysql

from .base_engine import BaseQueryEngine, QueryResult
from utils.logger import get_logger
from utils.exceptions import QueryEngineException

logger = get_logger(__name__)


class MySQLQueryEngine(BaseQueryEngine):
    """MySQL查询引擎"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 3306)
        self.database = config.get('database', 'test')
        self.user = config.get('user', 'root')
        self.password = config.get('password', '')
        self.charset = config.get('charset', 'utf8mb4')
        self.connection_pool = None
        self.pool_size = config.get('pool_size', 10)
        self.pool_timeout = config.get('pool_timeout', 30)
    
    async def connect(self) -> bool:
        """建立MySQL连接池"""
        try:
            # 创建连接池
            self.connection_pool = await aiomysql.create_pool(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                db=self.database,
                charset=self.charset,
                maxsize=self.pool_size,
                minsize=1,
                autocommit=True,
                pool_recycle=3600,  # 1小时回收连接
                echo=False
            )
            
            # 测试连接
            async with self.connection_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT 1")
                    result = await cursor.fetchone()
                    if result[0] != 1:
                        raise QueryEngineException("MySQL连接测试失败")
            
            self.is_connected = True
            logger.info(f"MySQL连接池创建成功: {self.host}:{self.port}/{self.database}")
            return True
            
        except Exception as e:
            logger.error(f"MySQL连接失败: {e}")
            raise QueryEngineException(f"MySQL连接失败: {e}")
    
    async def disconnect(self) -> bool:
        """关闭MySQL连接池"""
        try:
            if self.connection_pool:
                self.connection_pool.close()
                await self.connection_pool.wait_closed()
                self.connection_pool = None
                self.is_connected = False
                logger.info("MySQL连接池已关闭")
            return True
            
        except Exception as e:
            logger.error(f"MySQL连接池关闭失败: {e}")
            return False
    
    async def execute_query(
        self,
        sql: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None
    ) -> QueryResult:
        """执行MySQL查询"""
        if not self.is_connected:
            await self.connect()
        
        # 清理SQL
        sql = self._sanitize_sql(sql)
        
        try:
            start_time = time.time()
            
            async with self.connection_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # 设置查询超时
                    if timeout:
                        await cursor.execute(f"SET SESSION max_execution_time={timeout * 1000}")
                    
                    # 执行查询
                    if params:
                        await cursor.execute(sql, params)
                    else:
                        await cursor.execute(sql)
                    
                    # 获取结果
                    columns = [desc[0] for desc in cursor.description] if cursor.description else []
                    rows = await cursor.fetchall()
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            logger.info(f"MySQL查询执行成功，返回 {len(rows)} 行，耗时 {execution_time_ms}ms")
            
            return self._format_query_result(columns, list(rows), execution_time_ms, sql)
            
        except Exception as e:
            logger.error(f"MySQL查询执行失败: {e}")
            raise QueryEngineException(f"MySQL查询执行失败: {e}")
    
    async def get_schema_info(self, table_name: Optional[str] = None) -> Dict[str, Any]:
        """获取MySQL模式信息"""
        try:
            schema_info = {"tables": [], "columns": []}
            
            async with self.connection_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    if table_name:
                        # 获取指定表的列信息
                        columns_sql = """
                            SELECT 
                                COLUMN_NAME,
                                DATA_TYPE,
                                IS_NULLABLE,
                                COLUMN_DEFAULT,
                                COLUMN_KEY,
                                EXTRA,
                                COLUMN_COMMENT
                            FROM INFORMATION_SCHEMA.COLUMNS 
                            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                            ORDER BY ORDINAL_POSITION
                        """
                        await cursor.execute(columns_sql, [self.database, table_name])
                        columns = await cursor.fetchall()
                        
                        for col in columns:
                            schema_info["columns"].append({
                                "column_name": col[0],
                                "data_type": col[1],
                                "is_nullable": col[2] == 'YES',
                                "default_value": col[3],
                                "column_key": col[4],
                                "extra": col[5],
                                "comment": col[6]
                            })
                    else:
                        # 获取所有表信息
                        tables_sql = """
                            SELECT 
                                TABLE_NAME,
                                TABLE_TYPE,
                                TABLE_COMMENT,
                                TABLE_ROWS,
                                DATA_LENGTH
                            FROM INFORMATION_SCHEMA.TABLES 
                            WHERE TABLE_SCHEMA = %s
                            ORDER BY TABLE_NAME
                        """
                        await cursor.execute(tables_sql, [self.database])
                        tables = await cursor.fetchall()
                        
                        for table in tables:
                            schema_info["tables"].append({
                                "table_name": table[0],
                                "table_type": table[1],
                                "comment": table[2],
                                "estimated_rows": table[3],
                                "data_length": table[4]
                            })
            
            return schema_info
            
        except Exception as e:
            logger.error(f"获取MySQL模式信息失败: {e}")
            return {"tables": [], "columns": []}
    
    async def validate_sql(self, sql: str) -> Dict[str, Any]:
        """验证MySQL SQL语法"""
        try:
            sql = self._sanitize_sql(sql)
            
            async with self.connection_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # 使用EXPLAIN来验证SQL语法
                    explain_sql = f"EXPLAIN {sql}"
                    await cursor.execute(explain_sql)
                    await cursor.fetchall()  # 消费结果
            
            return {
                "valid": True,
                "errors": [],
                "warnings": []
            }
            
        except Exception as e:
            error_msg = str(e)
            return {
                "valid": False,
                "errors": [error_msg],
                "warnings": []
            }
    
    async def get_table_statistics(self, table_name: str) -> Dict[str, Any]:
        """获取MySQL表统计信息"""
        try:
            async with self.connection_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # 获取表基本信息
                    table_info_sql = """
                        SELECT 
                            TABLE_ROWS,
                            DATA_LENGTH,
                            INDEX_LENGTH,
                            DATA_FREE,
                            CREATE_TIME,
                            UPDATE_TIME
                        FROM INFORMATION_SCHEMA.TABLES 
                        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                    """
                    await cursor.execute(table_info_sql, [self.database, table_name])
                    table_info = await cursor.fetchone()
                    
                    if not table_info:
                        return {}
                    
                    # 获取索引信息
                    index_info_sql = """
                        SELECT 
                            INDEX_NAME,
                            COLUMN_NAME,
                            NON_UNIQUE,
                            INDEX_TYPE
                        FROM INFORMATION_SCHEMA.STATISTICS
                        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                        ORDER BY INDEX_NAME, SEQ_IN_INDEX
                    """
                    await cursor.execute(index_info_sql, [self.database, table_name])
                    indexes = await cursor.fetchall()
                    
                    # 组织索引信息
                    index_dict = {}
                    for idx in indexes:
                        index_name = idx[0]
                        if index_name not in index_dict:
                            index_dict[index_name] = {
                                "columns": [],
                                "unique": idx[2] == 0,
                                "type": idx[3]
                            }
                        index_dict[index_name]["columns"].append(idx[1])
                    
                    return {
                        "table_name": table_name,
                        "row_count": table_info[0] or 0,
                        "data_size_bytes": table_info[1] or 0,
                        "index_size_bytes": table_info[2] or 0,
                        "free_space_bytes": table_info[3] or 0,
                        "created_at": table_info[4].isoformat() if table_info[4] else None,
                        "updated_at": table_info[5].isoformat() if table_info[5] else None,
                        "indexes": index_dict
                    }
                    
        except Exception as e:
            logger.error(f"获取MySQL表统计信息失败: {e}")
            return {}
    
    async def estimate_query_cost(self, sql: str) -> Dict[str, Any]:
        """估算MySQL查询成本"""
        try:
            sql = self._sanitize_sql(sql)
            
            async with self.connection_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # 使用EXPLAIN FORMAT=JSON获取详细的执行计划
                    explain_sql = f"EXPLAIN FORMAT=JSON {sql}"
                    await cursor.execute(explain_sql)
                    result = await cursor.fetchone()
                    
                    if result:
                        import json
                        plan = json.loads(result[0])
                        
                        # 提取成本信息
                        query_block = plan.get("query_block", {})
                        cost_info = query_block.get("cost_info", {})
                        
                        return {
                            "estimated_rows": int(cost_info.get("read_cost", 0)),
                            "estimated_cost": float(cost_info.get("query_cost", 0)),
                            "estimated_time_ms": int(float(cost_info.get("query_cost", 0)) * 10),
                            "query_plan": plan
                        }
            
            return {
                "estimated_rows": 0,
                "estimated_cost": 0.0,
                "estimated_time_ms": 0
            }
            
        except Exception as e:
            logger.warning(f"MySQL查询成本估算失败: {e}")
            return {
                "estimated_rows": 0,
                "estimated_cost": 0.0,
                "estimated_time_ms": 0
            }
    
    async def optimize_table(self, table_name: str) -> Dict[str, Any]:
        """优化MySQL表"""
        try:
            async with self.connection_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # 执行OPTIMIZE TABLE
                    optimize_sql = f"OPTIMIZE TABLE {table_name}"
                    await cursor.execute(optimize_sql)
                    result = await cursor.fetchall()
                    
                    return {
                        "table_name": table_name,
                        "status": "success",
                        "details": list(result)
                    }
                    
        except Exception as e:
            logger.error(f"MySQL表优化失败: {e}")
            return {
                "table_name": table_name,
                "status": "error",
                "error": str(e)
            }
    
    async def analyze_table(self, table_name: str) -> Dict[str, Any]:
        """分析MySQL表"""
        try:
            async with self.connection_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # 执行ANALYZE TABLE
                    analyze_sql = f"ANALYZE TABLE {table_name}"
                    await cursor.execute(analyze_sql)
                    result = await cursor.fetchall()
                    
                    return {
                        "table_name": table_name,
                        "status": "success",
                        "details": list(result)
                    }
                    
        except Exception as e:
            logger.error(f"MySQL表分析失败: {e}")
            return {
                "table_name": table_name,
                "status": "error",
                "error": str(e)
            }
    
    async def get_connection_info(self) -> Dict[str, Any]:
        """获取MySQL连接信息"""
        try:
            async with self.connection_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # 获取版本信息
                    await cursor.execute("SELECT VERSION()")
                    version = await cursor.fetchone()
                    
                    # 获取连接数信息
                    await cursor.execute("SHOW STATUS LIKE 'Threads_connected'")
                    threads_connected = await cursor.fetchone()
                    
                    await cursor.execute("SHOW STATUS LIKE 'Max_used_connections'")
                    max_used_connections = await cursor.fetchone()
                    
                    # 获取数据库大小
                    size_sql = """
                        SELECT 
                            ROUND(SUM(DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024, 2) as size_mb
                        FROM INFORMATION_SCHEMA.TABLES 
                        WHERE TABLE_SCHEMA = %s
                    """
                    await cursor.execute(size_sql, [self.database])
                    db_size = await cursor.fetchone()
                    
                    return {
                        "version": version[0] if version else "unknown",
                        "database": self.database,
                        "host": self.host,
                        "port": self.port,
                        "threads_connected": int(threads_connected[1]) if threads_connected else 0,
                        "max_used_connections": int(max_used_connections[1]) if max_used_connections else 0,
                        "database_size_mb": float(db_size[0]) if db_size and db_size[0] else 0
                    }
                    
        except Exception as e:
            logger.error(f"获取MySQL连接信息失败: {e}")
            return {}
    
    def _get_supported_features(self) -> List[str]:
        """获取MySQL支持的功能"""
        return [
            "basic_query",
            "schema_inspection",
            "sql_validation", 
            "connection_test",
            "query_plan",
            "cost_estimation",
            "table_statistics",
            "table_optimization",
            "table_analysis",
            "connection_pool",
            "transaction_support",
            "prepared_statements"
        ]