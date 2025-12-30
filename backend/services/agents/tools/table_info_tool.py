"""
表信息查询工具

提供表的样例数据和统计信息查询功能，支持 diskcache 缓存。
缓存策略：
- 首次查询按 ETL_DATE=10天前 获取并缓存
- 缓存有效期100天
- 当元数据变化时缓存自动失效（基于元数据修改时间）
"""

import os
import json
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta

from diskcache import FanoutCache
from langchain.tools import tool, ToolRuntime
from langfuse import observe

from utils.logger import logger
from utils.config import settings
from models.db_base import get_db_session
from services.agents.models.deep_agent_context import DataAnalysisContext


# ==================== 缓存管理器 ====================

class TableInfoCache:
    """表信息缓存管理器"""

    # 缓存有效期（天）
    CACHE_EXPIRE_DAYS = 100

    def __init__(self, maxsize: int = 500 * 1024 * 1024):  # 500MB
        """
        初始化缓存管理器

        Args:
            maxsize: 最大缓存空间，默认500MB
        """
        self.cache = FanoutCache(
            directory=f"{settings.disk_cache_path}{os.sep}table_info_cache",
            shards=4,
            size_limit=maxsize,
        )
        # 过期时间（秒）
        self.expire_seconds = self.CACHE_EXPIRE_DAYS * 24 * 60 * 60

    def _build_cache_key(
        self,
        cache_type: str,
        table_name: str,
        metadata_updated_at: datetime,
        column_name: Optional[str] = None
    ) -> str:
        """
        构建缓存 key

        将元数据修改时间作为 key 的一部分，确保元数据变化时缓存自动失效

        Args:
            cache_type: 缓存类型（sample_data, table_stats, column_stats）
            table_name: 表名
            metadata_updated_at: 元数据最后修改时间
            column_name: 列名（仅 column_stats 需要）

        Returns:
            缓存 key
        """
        # 格式化时间到分钟级别（避免毫秒差异导致的问题）
        time_str = metadata_updated_at.strftime("%Y%m%d%H%M")

        if column_name:
            return f"{cache_type}:{table_name}:{column_name}:{time_str}"
        return f"{cache_type}:{table_name}:{time_str}"

    def get(
        self,
        cache_type: str,
        table_name: str,
        metadata_updated_at: datetime,
        column_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """获取缓存数据"""
        key = self._build_cache_key(cache_type, table_name, metadata_updated_at, column_name)
        result = self.cache.get(key)
        if result:
            logger.debug(f"缓存命中: {key}")
        return result

    def set(
        self,
        cache_type: str,
        table_name: str,
        metadata_updated_at: datetime,
        data: Dict[str, Any],
        column_name: Optional[str] = None
    ) -> None:
        """设置缓存数据"""
        key = self._build_cache_key(cache_type, table_name, metadata_updated_at, column_name)
        self.cache.set(key, data, expire=self.expire_seconds)
        logger.debug(f"缓存已设置: {key}, 过期时间: {self.CACHE_EXPIRE_DAYS}天")

    def clear_table_cache(self, table_name: str) -> int:
        """
        清除指定表的所有缓存（可选，用于手动清理）

        Args:
            table_name: 表名

        Returns:
            清除的缓存数量
        """
        count = 0
        for key in list(self.cache):
            if f":{table_name}:" in str(key):
                del self.cache[key]
                count += 1
        logger.info(f"清除表 {table_name} 的缓存: {count} 条")
        return count


# 全局缓存实例
table_info_cache = TableInfoCache()


# ==================== 辅助函数 ====================

def get_available_columns(table_name: str) -> Tuple[Optional[Dict], List[Dict], Optional[datetime]]:
    """
    获取表的可用列信息

    Args:
        table_name: 表名

    Returns:
        (table_info, columns, max_updated_at)
        - table_info: 表信息字典
        - columns: 可用列列表
        - max_updated_at: 元数据最晚修改时间
    """
    from models.metadata_models import MetadataTable, MetadataColumn

    with get_db_session() as db:
        # 查询表
        table = db.query(MetadataTable).filter(
            MetadataTable.name == table_name,
            MetadataTable.is_available == 0  # 0=可用
        ).first()

        if not table:
            return None, [], None

        # 查询可用列
        columns = db.query(MetadataColumn).filter(
            MetadataColumn.table_id == table.id,
            MetadataColumn.is_available == 0  # 0=可用
        ).all()

        # 计算最晚修改时间（表和所有列中的最大值）
        max_updated_at = table.updated_at
        for col in columns:
            if col.updated_at and col.updated_at > max_updated_at:
                max_updated_at = col.updated_at

        # 转换为字典
        table_info = {
            "id": table.id,
            "name": table.name,
            "comment": table.comment,
            "remark": table.remark
        }

        column_list = [
            {
                "name": col.name,
                "type": col.business_type,
                "comment": col.comment,
            }
            for col in columns
        ]

        return table_info, column_list, max_updated_at


def get_etl_date_10_days_ago() -> str:
    """获取10天前的日期字符串（格式：YYYY-MM-DD）"""
    return (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")


def is_numeric_type(col_type: str) -> bool:
    """判断是否为数值类型"""
    numeric_types = [
        'int', 'integer', 'bigint', 'smallint', 'tinyint',
        'float', 'double', 'decimal', 'numeric', 'real',
        'number', 'long'
    ]
    col_type_lower = col_type.lower()
    return any(nt in col_type_lower for nt in numeric_types)


# ==================== 工具函数 ====================

@observe(name="get_table_sample_data")
def get_table_sample_data(
    table_name: str,
    runtime: ToolRuntime["DataAnalysisContext"],
) -> str:
    """
    获取表的样例数据

    查询指定表 ETL_DATE=10天前 的样例数据，仅返回元数据中状态为可用的列。
    结果会被缓存100天，当元数据发生变化时缓存自动失效。

    Args:
        table_name: 库表名称

    Returns:
        JSON格式字符串，包含：
        - success: bool
        - table_name: str
        - etl_date: str (查询使用的ETL_DATE)
        - columns: list (可用列名列表)
        - row_count: int
        - data: list[dict] (样例数据)
        - from_cache: bool (是否来自缓存)
        - error: str (仅失败时)

    Examples:
        get_table_sample_data("hxb_dh_data.bcs_invm")
    """
    _ = runtime  # ToolRuntime 接口要求，当前未使用
    logger.info(f"查询表样例数据: {table_name}")

    try:
        # 获取可用列信息
        table_info, columns, max_updated_at = get_available_columns(table_name)

        if not table_info:
            return json.dumps({
                "success": False,
                "error": f"表 '{table_name}' 不存在或不可用"
            }, ensure_ascii=False)

        if not columns:
            return json.dumps({
                "success": False,
                "error": f"表 '{table_name}' 没有可用的列"
            }, ensure_ascii=False)

        # 尝试从缓存获取
        cached = table_info_cache.get("sample_data", table_name, max_updated_at)
        if cached:
            cached["from_cache"] = True
            return json.dumps(cached, ensure_ascii=False, default=str)

        # 构建查询
        etl_date = get_etl_date_10_days_ago()
        column_names = [col["name"] for col in columns]
        columns_sql = ", ".join(column_names)

        sql = f"""
            SELECT {columns_sql}
            FROM {table_name}
            WHERE ETL_DATE = '{etl_date}'
            LIMIT 20
        """

        # 执行查询
        from services.query_engine import get_query_engine
        engine = get_query_engine()
        result = engine.execute_query(sql)

        # 处理结果
        if hasattr(result, 'to_dict'):
            data = result.to_dict('records')
        elif isinstance(result, list):
            data = result
        else:
            data = []

        response = {
            "success": True,
            "table_name": table_name,
            "etl_date": etl_date,
            "columns": column_names,
            "row_count": len(data),
            "data": data,
            "from_cache": False
        }

        # 写入缓存
        table_info_cache.set("sample_data", table_name, max_updated_at, response)

        return json.dumps(response, ensure_ascii=False, default=str)

    except Exception as e:
        logger.error(f"查询表样例数据失败: {e}")
        return json.dumps({
            "success": False,
            "error": str(e)
        }, ensure_ascii=False)


@observe(name="get_table_statistics")
def get_table_statistics(
    table_name: str,
    runtime: ToolRuntime["DataAnalysisContext"]
) -> str:
    """
    获取表的统计信息

    查询指定表抽样日期的统计信息，包括：
    - 当天总条数
    - 各字段有值的条数（不为null且不为空字符串）

    Args:
        table_name: 库表名称

    Returns:
        JSON格式字符串，包含：
        - success: bool
        - table_name: str
        - etl_date: str
        - total_count: int (总条数)
        - column_stats: dict (各列的有值条数)
        - from_cache: bool
        - error: str (仅失败时)

    Examples:
        get_table_statistics("hxb_dh_data.bcs_invm")
    """
    _ = runtime  # ToolRuntime 接口要求，当前未使用
    logger.info(f"查询表统计信息: {table_name}")

    try:
        # 获取可用列信息
        table_info, columns, max_updated_at = get_available_columns(table_name)

        if not table_info:
            return json.dumps({
                "success": False,
                "error": f"表 '{table_name}' 不存在或不可用"
            }, ensure_ascii=False)

        if not columns:
            return json.dumps({
                "success": False,
                "error": f"表 '{table_name}' 没有可用的列"
            }, ensure_ascii=False)

        # 尝试从缓存获取
        cached = table_info_cache.get("table_stats", table_name, max_updated_at)
        if cached:
            cached["from_cache"] = True
            return json.dumps(cached, ensure_ascii=False, default=str)

        # 构建查询
        etl_date = get_etl_date_10_days_ago()

        # 构建各列的统计 SQL
        # COUNT(column) 会自动忽略 NULL
        # 对于字符串列，还需要排除空字符串
        count_expressions = []
        for col in columns:
            col_name = col["name"]
            col_type = col["type"]

            if is_numeric_type(col_type):
                # 数值类型：只需要排除 NULL
                count_expressions.append(f"COUNT({col_name}) AS {col_name}_count")
            else:
                # 字符串类型：排除 NULL 和空字符串
                count_expressions.append(
                    f"SUM(CASE WHEN {col_name} IS NOT NULL AND TRIM({col_name}) != '' THEN 1 ELSE 0 END) AS {col_name}_count"
                )

        count_sql = ", ".join(count_expressions)

        sql = f"""
            SELECT
                COUNT(*) AS total_count,
                {count_sql}
            FROM {table_name}
            WHERE ETL_DATE = '{etl_date}'
        """

        # 执行查询
        from services.query_engine import get_query_engine
        engine = get_query_engine()
        result = engine.execute_query(sql)

        # 处理结果
        if hasattr(result, 'to_dict'):
            data = result.to_dict('records')
        elif isinstance(result, list):
            data = result
        else:
            data = []

        if not data:
            return json.dumps({
                "success": False,
                "error": f"表 '{table_name}' 在 ETL_DATE={etl_date} 没有数据"
            }, ensure_ascii=False)

        row = data[0]
        total_count = row.get("total_count", 0)

        # 构建各列统计结果
        column_stats = {}
        for col in columns:
            col_name = col["name"]
            count_key = f"{col_name}_count"
            column_stats[col_name] = {
                "non_empty_count": row.get(count_key, 0),
                "type": col["type"],
                "comment": col["comment"]
            }

        response = {
            "success": True,
            "table_name": table_name,
            "etl_date": etl_date,
            "total_count": total_count,
            "column_stats": column_stats,
            "from_cache": False
        }

        # 写入缓存
        table_info_cache.set("table_stats", table_name, max_updated_at, response)

        return json.dumps(response, ensure_ascii=False, default=str)

    except Exception as e:
        logger.error(f"查询表统计信息失败: {e}")
        return json.dumps({
            "success": False,
            "error": str(e)
        }, ensure_ascii=False)


@observe(name="get_column_statistics")
def get_column_statistics(
    table_name: str,
    column_name: str,
    runtime: ToolRuntime["DataAnalysisContext"],
) -> str:
    """
    获取字段的详细统计信息

    查询指定表字段抽样日期的详细统计，包括：
    - 字段不重复值的条数
    - 取值范围：
      - 数值类型：最大值、最小值
      - 字符串类型：去重后的20个值

    Args:
        table_name: 库表表名称
        column_name: 列名称

    Returns:
        JSON格式字符串，包含：
        - success: bool
        - table_name: str
        - column_name: str
        - etl_date: str (抽样日期)
        - distinct_count: int (不重复值数量)
        - col_count: int (该字段etl_date的数据量)
        - value_range: dict (取值范围)
          - 数值类型: {"min": x, "max": y}
          - 字符串类型: {"sample_values": [...]}
        - from_cache: bool
        - error: str (仅失败时)

    Examples:
        get_column_statistics("hxb_dh_data.bcs_invm", "CURR_STATUS")
    """
    _ = runtime  # ToolRuntime 接口要求，当前未使用
    logger.info(f"查询字段统计信息: {table_name}.{column_name}")

    try:
        # 获取可用列信息
        table_info, columns, max_updated_at = get_available_columns(table_name)

        if not table_info:
            return json.dumps({
                "success": False,
                "error": f"表 '{table_name}' 不存在或不可用"
            }, ensure_ascii=False)

        # 查找指定列
        target_column = None
        for col in columns:
            if col["name"].lower() == column_name.lower():
                target_column = col
                break

        if not target_column:
            available_columns = [col["name"] for col in columns]
            return json.dumps({
                "success": False,
                "error": f"列 '{column_name}' 不存在或不可用。可用列: {available_columns}"
            }, ensure_ascii=False)

        # 尝试从缓存获取
        cached = table_info_cache.get("column_stats", table_name, max_updated_at, column_name)
        if cached:
            cached["from_cache"] = True
            return json.dumps(cached, ensure_ascii=False, default=str)

        # 构建查询
        etl_date = get_etl_date_10_days_ago()
        col_name = target_column["name"]
        col_type = target_column["type"]
        is_numeric = is_numeric_type(col_type)

        from services.query_engine import get_query_engine
        engine = get_query_engine()

        # 查询不重复值数量
        distinct_sql = f"""
            SELECT COUNT(DISTINCT {col_name}) AS distinct_count,
            COUNT({col_name}) AS col_count
            FROM {table_name}
            WHERE ETL_DATE = '{etl_date}'
        """
        distinct_result = engine.execute_query(distinct_sql)

        if hasattr(distinct_result, 'to_dict'):
            distinct_data = distinct_result.to_dict('records')
        elif isinstance(distinct_result, list):
            distinct_data = distinct_result
        else:
            distinct_data = []

        distinct_count = distinct_data[0].get("distinct_count", 0) if distinct_data else 0
        col_count = distinct_data[0].get("col_count", 0) if distinct_data else 0

        # 查询取值范围
        value_range = {}

        if is_numeric:
            # 数值类型：查询最大最小值
            range_sql = f"""
                SELECT
                    MIN({col_name}) AS min_value,
                    MAX({col_name}) AS max_value
                FROM {table_name}
                WHERE ETL_DATE = '{etl_date}'
                  AND {col_name} IS NOT NULL
            """
            range_result = engine.execute_query(range_sql)

            if hasattr(range_result, 'to_dict'):
                range_data = range_result.to_dict('records')
            elif isinstance(range_result, list):
                range_data = range_result
            else:
                range_data = []

            if range_data:
                value_range = {
                    "min": range_data[0].get("min_value"),
                    "max": range_data[0].get("max_value")
                }
        else:
            # 字符串类型：查询去重后的样本值
            sample_sql = f"""
                SELECT DISTINCT {col_name} AS value
                FROM {table_name}
                WHERE ETL_DATE = '{etl_date}'
                  AND {col_name} IS NOT NULL
                  AND TRIM({col_name}) != ''
                LIMIT 20
            """
            sample_result = engine.execute_query(sample_sql)

            if hasattr(sample_result, 'to_dict'):
                sample_data = sample_result.to_dict('records')
            elif isinstance(sample_result, list):
                sample_data = sample_result
            else:
                sample_data = []

            value_range = {
                "sample_values": [row.get("value") for row in sample_data]
            }

        response = {
            "success": True,
            "table_name": table_name,
            "column_name": col_name,
            "column_type": col_type,
            "column_comment": target_column["comment"],
            "etl_date": etl_date,
            "distinct_count": distinct_count,
            "col_count": col_count,
            "value_range": value_range,
            "from_cache": False
        }

        # 写入缓存
        table_info_cache.set("column_stats", table_name, max_updated_at, response, column_name)

        return json.dumps(response, ensure_ascii=False, default=str)

    except Exception as e:
        logger.error(f"查询字段统计信息失败: {e}")
        return json.dumps({
            "success": False,
            "error": str(e)
        }, ensure_ascii=False)
