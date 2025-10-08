"""
查询引擎抽象基类
定义查询引擎的统一接口
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import asyncio

from utils.logger import get_logger
from utils.exceptions import QueryEngineException

logger = get_logger(__name__)


class QueryResult:
    """查询结果封装类"""
    
    def __init__(
        self,
        columns: List[str],
        rows: List[List[Any]],
        row_count: int,
        execution_time_ms: int,
        sql: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.columns = columns
        self.rows = rows
        self.row_count = row_count
        self.execution_time_ms = execution_time_ms
        self.sql = sql
        self.metadata = metadata or {}
        self.created_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "columns": self.columns,
            "rows": self.rows,
            "row_count": self.row_count,
            "execution_time_ms": self.execution_time_ms,
            "sql": self.sql,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }
    
    def get_page(self, page: int, size: int) -> Dict[str, Any]:
        """获取分页数据"""
        start = (page - 1) * size
        end = start + size
        
        return {
            "columns": self.columns,
            "rows": self.rows[start:end],
            "page": page,
            "size": size,
            "total": self.row_count,
            "pages": (self.row_count + size - 1) // size
        }


class BaseQueryEngine(ABC):
    """查询引擎抽象基类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.connection = None
        self.connection_pool = None
        self.is_connected = False
    
    @abstractmethod
    async def connect(self) -> bool:
        """建立数据库连接"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """断开数据库连接"""
        pass
    
    @abstractmethod
    async def execute_query(
        self, 
        sql: str, 
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None
    ) -> QueryResult:
        """执行查询"""
        pass
    
    @abstractmethod
    async def get_schema_info(self, table_name: Optional[str] = None) -> Dict[str, Any]:
        """获取数据库模式信息"""
        pass
    
    @abstractmethod
    async def validate_sql(self, sql: str) -> Dict[str, Any]:
        """验证SQL语法"""
        pass
    
    async def test_connection(self) -> bool:
        """测试数据库连接"""
        try:
            test_sql = "SELECT 1 as test_connection"
            result = await self.execute_query(test_sql)
            return result.row_count > 0
        except Exception as e:
            logger.error(f"连接测试失败: {e}")
            return False
    
    async def execute_query_with_retry(
        self,
        sql: str,
        params: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> QueryResult:
        """带重试的查询执行"""
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                return await self.execute_query(sql, params)
            except Exception as e:
                last_exception = e
                logger.warning(f"查询执行失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (2 ** attempt))  # 指数退避
                else:
                    break
        
        raise QueryEngineException(f"查询执行失败，已重试 {max_retries} 次: {last_exception}")
    
    def _sanitize_sql(self, sql: str) -> str:
        """清理SQL语句"""
        if not sql:
            raise QueryEngineException("SQL语句不能为空")
        
        # 移除多余空白字符
        sql = sql.strip()
        
        # 基础安全检查
        dangerous_keywords = [
            'DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE',
            'INSERT', 'UPDATE', 'GRANT', 'REVOKE'
        ]
        
        sql_upper = sql.upper()
        for keyword in dangerous_keywords:
            if f' {keyword} ' in f' {sql_upper} ':
                raise QueryEngineException(f"不允许执行包含 {keyword} 的操作")
        
        return sql
    
    def _parse_connection_string(self, connection_string: str) -> Dict[str, str]:
        """解析连接字符串"""
        # 简单的连接字符串解析逻辑
        # 格式: "engine://user:password@host:port/database"
        parts = {}
        
        try:
            if '://' in connection_string:
                engine_part, rest = connection_string.split('://', 1)
                parts['engine'] = engine_part
                
                if '@' in rest:
                    auth_part, host_part = rest.rsplit('@', 1)
                    if ':' in auth_part:
                        parts['user'], parts['password'] = auth_part.split(':', 1)
                    else:
                        parts['user'] = auth_part
                else:
                    host_part = rest
                
                if '/' in host_part:
                    host_port, parts['database'] = host_part.split('/', 1)
                else:
                    host_port = host_part
                
                if ':' in host_port:
                    parts['host'], parts['port'] = host_port.split(':', 1)
                    parts['port'] = int(parts['port'])
                else:
                    parts['host'] = host_port
            
            return parts
            
        except Exception as e:
            raise QueryEngineException(f"连接字符串解析失败: {e}")
    
    def _format_query_result(
        self,
        columns: List[str],
        rows: List[List[Any]],
        execution_time_ms: int,
        sql: str
    ) -> QueryResult:
        """格式化查询结果"""
        # 数据类型转换和格式化
        formatted_rows = []
        
        for row in rows:
            formatted_row = []
            for value in row:
                # 处理特殊数据类型
                if isinstance(value, datetime):
                    formatted_row.append(value.isoformat())
                elif value is None:
                    formatted_row.append(None)
                else:
                    formatted_row.append(value)
            formatted_rows.append(formatted_row)
        
        return QueryResult(
            columns=columns,
            rows=formatted_rows,
            row_count=len(formatted_rows),
            execution_time_ms=execution_time_ms,
            sql=sql
        )
    
    async def get_table_list(self) -> List[Dict[str, str]]:
        """获取表列表"""
        try:
            schema_info = await self.get_schema_info()
            return schema_info.get('tables', [])
        except Exception as e:
            logger.error(f"获取表列表失败: {e}")
            return []
    
    async def get_table_columns(self, table_name: str) -> List[Dict[str, Any]]:
        """获取表的列信息"""
        try:
            schema_info = await self.get_schema_info(table_name)
            return schema_info.get('columns', [])
        except Exception as e:
            logger.error(f"获取表列信息失败: {e}")
            return []
    
    async def estimate_query_cost(self, sql: str) -> Dict[str, Any]:
        """估算查询成本（可选实现）"""
        return {
            "estimated_rows": 0,
            "estimated_cost": 0.0,
            "estimated_time_ms": 0
        }
    
    def get_engine_info(self) -> Dict[str, Any]:
        """获取引擎信息"""
        return {
            "engine_type": self.__class__.__name__,
            "version": "1.0.0",
            "config": {k: v for k, v in self.config.items() if 'password' not in k.lower()},
            "is_connected": self.is_connected,
            "features": self._get_supported_features()
        }
    
    def _get_supported_features(self) -> List[str]:
        """获取支持的功能列表"""
        return [
            "basic_query",
            "schema_inspection",
            "sql_validation",
            "connection_test"
        ]