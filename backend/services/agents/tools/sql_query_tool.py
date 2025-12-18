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
    engine_type: Optional[str] = None,
    limit: int = 1000
) -> str:
    """
    执行 SQL 查询并返回结果

    Args:
        sql: SQL 查询语句。支持标准 SQL 语法，可以进行 SELECT、JOIN、GROUP BY 等操作
        engine_type: 查询引擎类型，可选值: "duckdb"、"spark"、"empty"。
                    默认使用配置文件中的引擎类型
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
        sql_query("SELECT * FROM users WHERE age > 18")

        # 聚合查询
        sql_query("SELECT department, COUNT(*) as cnt FROM employees GROUP BY department")

        # 指定引擎
        sql_query("SELECT * FROM sales", engine_type="spark")

        # 不限制行数
        sql_query("SELECT * FROM large_table", limit=0)
    """
    logger.info(f"执行SQL查询: {sql[:100]}...")

    try:
        # 延迟导入，避免循环依赖
        from services.query_engine import get_query_engine

        # 获取查询引擎
        engine = get_query_engine(engine_type)

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


@observe(name="get_table_schema")
def get_table_schema(table_name: str, engine_type: Optional[str] = None) -> str:
    """
    获取表结构信息

    Args:
        table_name: 表名
        engine_type: 查询引擎类型

    Returns:
        JSON 格式的表结构信息
    """
    logger.info(f"获取表结构: {table_name}")

    try:
        from services.query_engine import get_query_engine

        engine = get_query_engine(engine_type)

        # 不同引擎使用不同的语法获取表结构
        # DuckDB 和 Spark 都支持 DESCRIBE
        result = engine.execute_query(f"DESCRIBE {table_name}")

        if hasattr(result, 'to_dict'):
            schema_data = result.to_dict('records')
        else:
            schema_data = result

        return json.dumps({
            "success": True,
            "table_name": table_name,
            "schema": schema_data
        }, ensure_ascii=False, default=str)

    except Exception as e:
        logger.error(f"获取表结构失败: {e}")
        return json.dumps({
            "success": False,
            "table_name": table_name,
            "error": str(e)
        }, ensure_ascii=False)


@observe(name="list_tables")
def list_tables(engine_type: Optional[str] = None) -> str:
    """
    列出所有可用的表

    Args:
        engine_type: 查询引擎类型

    Returns:
        JSON 格式的表列表
    """
    logger.info("列出所有表")

    try:
        from services.query_engine import get_query_engine

        engine = get_query_engine(engine_type)

        # DuckDB 使用 SHOW TABLES，Spark 也支持
        result = engine.execute_query("SHOW TABLES")

        if hasattr(result, 'to_dict'):
            tables = result.to_dict('records')
        else:
            tables = result

        return json.dumps({
            "success": True,
            "tables": tables
        }, ensure_ascii=False, default=str)

    except Exception as e:
        logger.error(f"列出表失败: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "tables": []
        }, ensure_ascii=False)
