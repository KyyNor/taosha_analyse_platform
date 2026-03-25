"""
字段值样本增强服务

从数据库采样字段的实际值，为Schema摘要提供数据基础。
支持不同类型字段的采样策略，并自动添加日期分区条件以避免全表扫描。
"""

import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from models.db_base import get_db_session
from models.metadata_models import MetadataColumn
from sqlalchemy.orm import Session

from utils.logger import LoggerMixin
from utils.config import settings
from repositories.metadata_repository import MetadataColumnRepository, MetadataTableRepository
from services.query_engine.base import QueryEngineFactory


class FieldValueSampler(LoggerMixin):
    """字段值采样服务

    从数据库采样字段的实际值，支持多种采样策略：
    - 枚举型/低基数：采样所有去重值
    - 数值型：采样min、max、平均值+随机样例
    - 文本型：采样TOP 20（按频次或随机）
    - 日期型：采样范围

    重要：对于Hadoop大数据表，自动检测并添加日期分区条件（etl_date或cdate）

    连接管理：如果不传入 db，则在需要时内部自行获取连接，
    使用完后立即释放，避免长时间持有连接导致超时。
    """

    # 常见的日期分区字段名
    DATE_PARTITION_FIELDS = ['etl_date', 'cdate']

    # 字段类型映射
    NUMERIC_TYPES = ['int', 'bigint', 'smallint', 'tinyint', 'decimal', 'double', 'float']
    STRING_TYPES = ['varchar', 'char', 'text', 'string']
    DATE_TYPES = ['date', 'datetime', 'timestamp', 'time']

    def __init__(self):
        """初始化字段值采样服务
        """
        # 初始化查询引擎（用于采样查询）
        try:
            self.query_engine = QueryEngineFactory.create_service(
                service_type=settings.query_engine_type
            )
            self.logger.info(f"查询引擎初始化成功: {settings.query_engine_type}")
        except Exception as e:
            self.logger.warning(f"查询引擎初始化失败: {e}，采样功能将不可用")
            self.query_engine = None

        # 采样结果缓存
        self._cache: Dict[str, Dict] = {}

        # 日期分区字段缓存（避免重复查询元数据库）
        self._date_partition_cache: Dict[str, Optional[str]] = {}

    def sample_field_values(
        self,
        table_name: str,
        column_name: str,
        column_type: str,
        table_id: int,
        limit: int = 20,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """采样字段值

        Args:
            table_name: 表名
            column_name: 字段名
            column_type: 字段类型
            limit: 采样数量限制
            use_cache: 是否使用缓存

        Returns:
            采样结果字典，包含：
            - values: 采样值列表
            - count: 去重值数量
            - sample_type: 采样类型（distinct/stats/range）
            - stats: 统计信息（仅数值型）
        """
        # 检查缓存
        cache_key = f"{table_name}.{column_name}"
        if use_cache and cache_key in self._cache:
            self.logger.debug(f"从缓存获取字段值样本: {cache_key}")
            return self._cache[cache_key]

        # 如果查询引擎不可用，返回空结果
        if not self.query_engine:
            return {
                "values": [],
                "count": 0,
                "sample_type": "none",
                "stats": {}
            }

        try:
            # 根据字段类型选择采样策略
            if self._is_numeric_type(column_type):
                result = self._sample_numeric_field(table_id, table_name, column_name, limit)
            elif self._is_date_type(column_type):
                result = self._sample_date_field(table_id, table_name, column_name)
            elif self._is_string_type(column_type):
                result = self._sample_string_field(table_id, table_name, column_name, limit)
            else:
                # 其他类型，尝试简单采样
                result = self._sample_generic_field(table_id, table_name, column_name, limit)

            # 缓存结果
            if use_cache:
                self._cache[cache_key] = result

            return result

        except Exception as e:
            self.logger.error(f"采样字段值失败 {table_name}.{column_name}: {e}")
            return {
                "values": [],
                "count": 0,
                "sample_type": "error",
                "error": str(e)
            }

    def sample_table_fields(
        self,
        table_id: int,
        limit: int = 20,
    ) -> Dict[str, Dict]:
        """采样表的所有字段

        注意：此方法需要调用方在 with get_db_session() 块内调用，或传入 db 参数。

        Args:
            table_id: 表ID
            limit: 每个字段的采样数量限制

        Returns:
            字段名到采样结果的映射
        """
        try:            
            with get_db_session() as db:
                column_repo = MetadataColumnRepository(db)
                # 获取表的所有字段
                columns = column_repo.get_by_table_id(table_id)

                # 过滤可用的字段
                available_columns = [col for col in columns if col.is_available == 0]

                results = {}
                for col in available_columns:
                    # 从表名中提取（可能包含数据库前缀）
                    table_name = col.table.name
                    column_name = col.name
                    column_type = col.type

                    sample_result = self.sample_field_values(
                        table_name=table_name,
                        column_name=column_name,
                        column_type=column_type,
                        table_id=table_id,
                        limit=limit
                    )

                    results[column_name] = sample_result

            return results

        except Exception as e:
            self.logger.error(f"采样表字段失败 table_id={table_id}: {e}")
            return {}

    def _detect_date_partition_column(self, table_id: int) -> Optional[str]:
        """检测表的日期分区字段

        使用缓存避免重复查询元数据库

        Args:
            table_id: 表ID
            db: 数据库会话（由调用方管理生命周期）

        Returns:
            日期分区字段名，如果未找到则返回None
        """
        # 使用传入的 db 或者自身的 db
        effective_db = db if db else self.db

        if not effective_db:
            return None

        # 检查缓存
        if table_id in self._date_partition_cache:
            return self._date_partition_cache[table_id]

        try:
            with get_db_session() as db:
                table_repo = MetadataTableRepository(db)
                column_repo = MetadataColumnRepository(db)
                # 根据表名获取表信息
                table = table_repo.get_by_id(table_id)
                if not table:
                    table_name = "unknown"
                else:
                    table_name = table.name

                if not table:
                    # 未找到表，缓存None
                    self._date_partition_cache[table_id] = None
                    return None

                # 获取该表的所有字段
                columns = column_repo.get_by_table_id(table_id)

                # 查找可能的日期分区字段
                for col in columns:
                    if col.name.lower() in self.DATE_PARTITION_FIELDS:
                        self.logger.info(f"检测到日期分区字段: {col.name} (表: {table_name})")
                        # 缓存结果
                        self._date_partition_cache[table_id] = col.name
                        return col.name

                # 未找到日期分区字段，缓存None避免重复查询
                self._date_partition_cache[table_id] = None
                return None

        except Exception as e:
            self.logger.warning(f"检测日期分区字段失败 (表: {table_name}): {e}")
            # 出错时也缓存None，避免重复出错
            self._date_partition_cache[table_id] = None
            return None

    def _build_sample_query(
        self,
        table_id: int,
        table_name: str,
        select_clause: str,
        where_clause: Optional[str] = None,
        order_by: Optional[str] = None,
        group_by: Optional[str] = None,
        limit: int = 20
    ) -> str:
        """构建采样查询SQL

        自动添加日期分区条件以避免全表扫描

        Args:
            table_name: 表名
            select_clause: SELECT子句
            where_clause: WHERE子句（可选）
            order_by: ORDER BY子句（可选）
            limit: 限制数量

        Returns:
            完整的SQL查询语句
        """
        # 检测日期分区字段
        date_partition_col = self._detect_date_partition_column(table_id)

        # 构建WHERE子句
        conditions = []

        # 添加日期分区条件
        if date_partition_col:
            # 获取最近的日期（假设最近7天有数据）
            recent_date = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
            conditions.append(f"{date_partition_col} = '{recent_date}'")
            self.logger.debug(f"添加日期分区条件: {date_partition_col} = '{recent_date}'")

        # 添加自定义条件
        if where_clause:
            conditions.append(where_clause)

        # 组合WHERE子句
        where_sql = ""
        if conditions:
            where_sql = "WHERE " + " AND ".join(conditions)

        # 构建ORDER BY子句
        order_sql = f"ORDER BY {order_by}" if order_by else ""

        group_by_sql = ""
        if group_by:
            group_by_sql = f"GROUP BY {group_by}"

        # 构建完整SQL
        query = f"""
            SELECT {select_clause}
            FROM {table_name}
            {where_sql}
            {group_by_sql}
            {order_sql}
            LIMIT {limit}
        """

        return query.strip()

    def _sample_numeric_field(
        self,
        table_id: int,
        table_name: str,
        column_name: str,
        limit: int
    ) -> Dict[str, Any]:
        """采样数值型字段

        采集统计信息（min、max、avg）和随机样例

        Args:
            table_name: 表名
            column_name: 字段名
            limit: 采样数量

        Returns:
            采样结果
        """
        try:
            # 查询统计信息
            stats_query = self._build_sample_query(
                table_id=table_id,
                table_name=table_name,
                select_clause=f"MIN({column_name}) as min_val, MAX({column_name}) as max_val, AVG({column_name}) as avg_val, COUNT(DISTINCT {column_name}) as distinct_count",
                limit=1
            )

            stats_result = self.query_engine.execute_query(stats_query)

            if not stats_result or len(stats_result) == 0:
                return {
                    "values": [],
                    "count": 0,
                    "sample_type": "stats",
                    "stats": {}
                }

            stats = stats_result[0]

            # 查询随机样例
            sample_query = self._build_sample_query(
                table_id=table_id,
                table_name=table_name,
                select_clause=column_name,
                order_by=f"RAND()",
                limit=min(5, limit)
            )

            sample_result = self.query_engine.execute_query(sample_query)
            sample_values = [row.get(column_name) for row in sample_result if row.get(column_name) is not None]

            return {
                "values": sample_values,
                "count": int(stats.get('distinct_count', 0)),
                "sample_type": "stats",
                "stats": {
                    "min": float(stats.get('min_val', 0)) if stats.get('min_val') is not None else None,
                    "max": float(stats.get('max_val', 0)) if stats.get('max_val') is not None else None,
                    "avg": float(stats.get('avg_val', 0)) if stats.get('avg_val') is not None else None
                }
            }

        except Exception as e:
            self.logger.error(f"采样数值字段失败: {e}")
            return {
                "values": [],
                "count": 0,
                "sample_type": "error",
                "stats": {},
                "error": str(e)
            }

    def _sample_string_field(
        self,
        table_id: int,
        table_name: str,
        column_name: str,
        limit: int
    ) -> Dict[str, Any]:
        """采样字符串型字段

        采集TOP去重值（按频次排序）

        Args:
            table_name: 表名
            column_name: 字段名
            limit: 采样数量

        Returns:
            采样结果
        """
        try:
            # 查询去重值数量
            count_query = self._build_sample_query(
                table_id=table_id,
                table_name=table_name,
                select_clause=f"COUNT(DISTINCT {column_name}) as distinct_count",
                limit=1
            )

            count_result = self.query_engine.execute_query(count_query)
            distinct_count = count_result[0].get('distinct_count', 0) if count_result else 0

            # 如果去重值较少（< 100），查询所有去重值
            if distinct_count and distinct_count < 100:
                values_query = self._build_sample_query(
                    table_id=table_id,
                    table_name=table_name,
                    select_clause=f"DISTINCT {column_name} as value",
                    order_by='value',
                    limit=limit
                )
            else:
                # 否则查询频次最高的值
                values_query = self._build_sample_query(
                    table_id=table_id,
                    table_name=table_name,
                    select_clause=f"{column_name} as value, COUNT(*) as cnt",
                    where_clause=f"{column_name} IS NOT NULL",
                    order_by="cnt DESC",
                    group_by=column_name,
                    limit=limit
                )

            values_result = self.query_engine.execute_query(values_query)
            values = [row.get('value') for row in values_result if row.get('value') is not None]

            return {
                "values": values[:limit],
                "count": int(distinct_count) if distinct_count else len(values),
                "sample_type": "distinct",
                "stats": {}
            }

        except Exception as e:
            self.logger.error(f"采样字符串字段失败: {e}")
            return {
                "values": [],
                "count": 0,
                "sample_type": "error",
                "stats": {},
                "error": str(e)
            }

    def _sample_date_field(
        self,
        table_id: int,
        table_name: str,
        column_name: str
    ) -> Dict[str, Any]:
        """采样日期型字段

        采集日期范围

        Args:
            table_name: 表名
            column_name: 字段名

        Returns:
            采样结果
        """
        try:
            # 查询日期范围
            range_query = self._build_sample_query(
                table_id=table_id,
                table_name=table_name,
                select_clause=f"MIN({column_name}) as min_date, MAX({column_name}) as max_date, COUNT(DISTINCT {column_name}) as distinct_count",
                limit=1
            )

            range_result = self.query_engine.execute_query(range_query)

            if not range_result or len(range_result) == 0:
                return {
                    "values": [],
                    "count": 0,
                    "sample_type": "range",
                    "stats": {}
                }

            row = range_result[0]
            min_date = row.get('min_date')
            max_date = row.get('max_date')
            distinct_count = row.get('distinct_count', 0)

            # 查询几个样例日期
            sample_query = self._build_sample_query(
                table_id=table_id,
                table_name=table_name,
                select_clause=column_name,
                where_clause=f"{column_name} IS NOT NULL",
                order_by=column_name,
                limit=5
            )

            sample_result = self.query_engine.execute_query(sample_query)
            sample_values = [row.get(column_name) for row in sample_result if row.get(column_name) is not None]

            return {
                "values": sample_values,
                "count": int(distinct_count) if distinct_count else 0,
                "sample_type": "range",
                "stats": {
                    "min_date": str(min_date) if min_date else None,
                    "max_date": str(max_date) if max_date else None
                }
            }

        except Exception as e:
            self.logger.error(f"采样日期字段失败: {e}")
            return {
                "values": [],
                "count": 0,
                "sample_type": "error",
                "stats": {},
                "error": str(e)
            }

    def _sample_generic_field(
        self,
        table_id: int,
        table_name: str,
        column_name: str,
        limit: int
    ) -> Dict[str, Any]:
        """通用字段采样

        Args:
            table_name: 表名
            column_name: 字段名
            limit: 采样数量

        Returns:
            采样结果
        """
        try:
            query = self._build_sample_query(
                table_id=table_id,
                table_name=table_name,
                select_clause=column_name,
                where_clause=f"{column_name} IS NOT NULL",
                order_by=f"RAND()",
                limit=limit
            )

            result = self.query_engine.execute_query(query)
            values = [row.get(column_name) for row in result if row.get(column_name) is not None]

            return {
                "values": values,
                "count": len(values),
                "sample_type": "generic",
                "stats": {}
            }

        except Exception as e:
            self.logger.error(f"通用字段采样失败: {e}")
            return {
                "values": [],
                "count": 0,
                "sample_type": "error",
                "stats": {},
                "error": str(e)
            }

    def _is_numeric_type(self, column_type: str) -> bool:
        """判断是否为数值类型"""
        return any(col_type in column_type.lower() for col_type in self.NUMERIC_TYPES)

    def _is_string_type(self, column_type: str) -> bool:
        """判断是否为字符串类型"""
        return any(col_type in column_type.lower() for col_type in self.STRING_TYPES)

    def _is_date_type(self, column_type: str) -> bool:
        """判断是否为日期类型"""
        return any(col_type in column_type.lower() for col_type in self.DATE_TYPES)

    def clear_cache(self):
        """清空采样缓存"""
        self._cache.clear()
        self.logger.info("字段值采样缓存已清空")

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return {
            "cached_fields": len(self._cache),
            "cache_keys": list(self._cache.keys())
        }
