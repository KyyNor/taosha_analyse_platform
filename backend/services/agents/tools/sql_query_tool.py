"""
SQL 查询工具
用于执行 SQL 查询获取数据，支持 DuckDB 和 Spark 引擎
"""

import json
from typing import TYPE_CHECKING
from pathlib import Path
from datetime import datetime
from langfuse import observe
from langchain.tools import tool, ToolRuntime
from utils.logger import logger

if TYPE_CHECKING:
    from services.agents.deepagents.data_analyser_agent import DataAnalysisContext


@tool
@observe(name="sql_query")
def sql_query(
    sql: str,
    runtime: ToolRuntime["DataAnalysisContext"],
    limit: int = 1000,
    save_to_file: bool = True
) -> str:
    """
    执行 SQL 查询并返回结果
    注意，查询除hxb_dh_data_dim外的表<important>必须带ETL_DATE/CDATE查询条件</important>

    Args:
        sql: SQL 查询语句。支持标准 SQL 语法，可以进行 SELECT、JOIN、GROUP BY 等操作
        limit: 结果行数限制，默认 1000 行。设置为 0 则不限制
        save_to_file: 是否将查询结果保存到文件，默认 True。如果为 True，结果会保存为 CSV 格式

    Returns:
        JSON 格式的查询结果字符串，包含以下字段:
        - success: bool, 是否成功
        - row_count: int, 返回的行数
        - columns: list, 列名列表
        - data: list[dict], 查询结果数据（如果保存到文件，此字段为空列表）
        - sql: str, 实际执行的 SQL
        - file_path: str, 保存的文件相对路径（仅在 save_to_file=True 时）
        - error: str, 错误信息（仅在失败时）

    Examples:
        # 简单查询
        sql_query("SELECT * FROM users WHERE ETL_DATE='2025-09-30' AND age > 18")

        # 聚合查询
        sql_query("SELECT department, COUNT(*) as cnt FROM employees WHERE ETL_DATE='2025-09-30'  GROUP BY department")

        # 不限制行数
        sql_query("SELECT * FROM large_table WHERE ETL_DATE='2025-09-30' ", limit=0)

        # 不保存到文件
        sql_query("SELECT * FROM large_table WHERE ETL_DATE='2025-09-30'", save_to_file=False)
    """
    # 从运行时上下文获取配置
    ctx = runtime.context
    session_id = ctx.session_id

    logger.info(f"[会话 {session_id}] 执行SQL查询: {sql[:100]}...")

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

        # 如果需要保存到文件
        result = {
            "success": True,
            "row_count": len(data),
            "columns": columns,
            "sql": sql
        }

        if save_to_file:
            try:
                # 获取输出目录
                output_dir = Path(ctx.output_dir)
                output_dir.mkdir(parents=True, exist_ok=True)

                # 生成文件名（使用时间戳）
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"query_result_{timestamp}.csv"
                file_path = output_dir / filename

                # 保存为CSV
                import pandas as pd
                df = pd.DataFrame(data)
                df.to_csv(file_path, index=False, encoding="utf-8-sig")

                # 计算相对路径（相对于output_dir的父目录）
                relative_path = file_path.name

                logger.info(f"查询结果已保存到文件: {relative_path}")

                result["file_path"] = relative_path
                result["data"] = []  # 保存到文件时不返回数据，减少内存占用

            except Exception as file_error:
                logger.error(f"保存文件失败: {file_error}")
                result["data"] = data
                result["warning"] = f"保存文件失败: {str(file_error)}"
        else:
            result["data"] = data

        return json.dumps(result, ensure_ascii=False, default=str)

    except Exception as e:
        logger.error(f"SQL查询失败: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "sql": sql,
            "row_count": 0,
            "data": []
        }, ensure_ascii=False)
