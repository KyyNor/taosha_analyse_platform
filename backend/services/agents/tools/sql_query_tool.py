"""
SQL 查询工具
用于执行 SQL 查询获取数据，支持 DuckDB 和 Spark 引擎
"""

import json
from typing import Optional
from langfuse import observe
from utils.logger import logger


@observe(name="sql_query")
def sql_query(
    sql: str,
    limit: int = 1000
) -> str:
    """
    执行 SQL 查询并返回结果
    注意，查询除hxb_dh_data_dim外的表<important>必须带ETL_DATE/CDATE查询条件</important>

    Args:
        sql: SQL 查询语句。支持标准 SQL 语法，可以进行 SELECT、JOIN、GROUP BY 等操作
        limit: 结果行数限制，默认 1000 行。设置为 0 则不限制

    Returns:
        JSON 格式的查询结果字符串，包含以下字段:
        - success: bool, 是否成功
        - row_count: int, 返回的行数
        - columns: list, 列名列表
        - data: list[dict], 查询结果数据
        - sql: str, 实际执行的 SQL
        - error: str, 错误信息（仅在失败时）

    Examples:
        # 简单查询
        sql_query("SELECT * FROM users WHERE ETL_DATE='2025-09-30' AND age > 18")

        # 聚合查询
        sql_query("SELECT department, COUNT(*) as cnt FROM employees WHERE ETL_DATE='2025-09-30'  GROUP BY department")

        # 不限制行数
        sql_query("SELECT * FROM large_table WHERE ETL_DATE='2025-09-30' ", limit=0)
    """
    logger.info(f"执行SQL查询: {sql[:100]}...")

    try:
        # 延迟导入，避免循环依赖
        from services.query_engine import get_query_engine

        # 获取查询引擎
        engine = get_query_engine()

        # 处理 LIMIT 子句
        sql_upper = sql.upper().strip()
        if limit > 0 and "LIMIT" not in sql_upper:
            # 移除末尾的分号
            sql = sql.rstrip().rstrip(";")
            sql = f"{sql} LIMIT {limit}"

        # 执行查询
        result = engine.execute_query(sql)

        # 处理结果
        if hasattr(result, 'to_dict'):
            # DataFrame 类型
            data = result.to_dict('records')
            columns = list(result.columns) if hasattr(result, 'columns') else []
        elif isinstance(result, list):
            data = result
            columns = list(result[0].keys()) if result and isinstance(result[0], dict) else []
        else:
            data = []
            columns = []

        # 应用 limit
        if limit > 0:
            data = data[:limit]

        logger.info(f"SQL查询成功，返回 {len(data)} 行数据")

        return json.dumps({
            "success": True,
            "row_count": len(data),
            "columns": columns,
            "data": data,
            "sql": sql
        }, ensure_ascii=False, default=str)

    except Exception as e:
        logger.error(f"SQL查询失败: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "sql": sql,
            "row_count": 0,
            "data": []
        }, ensure_ascii=False)
