"""
SQL 查询工具
用于执行 SQL 查询获取数据，支持 DuckDB 和 Spark 引擎
"""

import json
import re
from typing import TYPE_CHECKING, Optional
from pathlib import Path
from datetime import datetime
from langfuse import observe
from langchain.tools import tool, ToolRuntime
from utils.logger import logger

from services.agents.models.deep_agent_context import DataAnalysisContext


@tool
@observe(name="sql_query")
def sql_query(
    sql: str,
    runtime: ToolRuntime["DataAnalysisContext"],
    limit: int = 1000,
    save_to_file: bool = True,
    file_description: Optional[str] = None
) -> str:
    """
    执行 SQL 查询并返回结果
    注意，查询除hxb_dh_data_dim外的表必须带ETL_DATE/CDATE查询条件

    Args:
        sql: SQL 查询语句
        limit: 结果行数限制，默认1000行。设置为0则不限制
        save_to_file: 是否保存到文件，默认True
            - True: 返回文件路径，data字段为空。后续用shell工具查询/分析
            - False: 返回完整数据。仅适合小结果集（<100行）或聚合查询
        file_description: 文件描述，用于生成有意义的文件名
            - 输出文件名： {file_description}_{timestamp}.csv
            - 建议50字符内，支持中文但推荐英文

    Returns:
        JSON格式字符串，包含：
        - success: bool
        - row_count: int
        - columns: list
        - data: list[dict] (save_to_file=True时为空)
        - file_path: str (仅save_to_file=True时存在)
        - error: str (仅失败时)

    Examples:
        # 大数据集查询（推荐）
        sql_query("SELECT * FROM orders WHERE ETL_DATE='2025-09-30'", file_description="pending_orders")
        # 生成: pending_orders_20251223_143025.csv

        # 聚合查询直接返回
        sql_query("SELECT status, COUNT(*) FROM orders WHERE ETL_DATE='2025-09-30' GROUP BY status",
                  save_to_file=False, file_description="order_status")
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
        }

        if save_to_file:
            try:
                # 获取输出目录
                output_dir = Path(ctx.output_dir)
                output_dir.mkdir(parents=True, exist_ok=True)

                # 生成文件名（使用时间戳）
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

                # 处理文件描述
                if file_description:
                    # 清理特殊字符，保留字母数字、下划线、连字符、中文
                    safe_desc = re.sub(r'[^\w\s\-\u4e00-\u9fff]', '', file_description)
                    # 将空格和多个连字符统一为单个下划线
                    safe_desc = re.sub(r'[\s\-]+', '_', safe_desc).strip('_')
                    # 建议性提示
                    if len(safe_desc) > 100:
                        logger.warning(f"文件描述过长({len(safe_desc)}字符)，建议控制在100字符内")
                    filename = f"{safe_desc}_{timestamp}.csv"
                else:
                    filename = f"query_result_{timestamp}.csv"

                file_path = output_dir / filename

                # 保存为CSV
                import pandas as pd
                df = pd.DataFrame(data)
                df.to_csv(file_path, index=False, encoding="utf-8-sig")

                # 计算相对路径（相对于output_dir的父目录）
                relative_path = file_path.name

                logger.info(f"查询结果已保存到文件: {relative_path}")

                result["file_path"] = "/analysis/" + relative_path
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
            "row_count": 0,
            "data": []
        }, ensure_ascii=False)


@tool
@observe(name="execute_sql_query")
def execute_sql_query(
    sql: str,
    runtime: ToolRuntime["DataAnalysisContext"],
    limit: int = 100
) -> str:
    """
    执行 SQL 查询并直接返回数据结果
    注意，查询除hxb_dh_data_dim外的表必须带ETL_DATE/CDATE查询条件

    Args:
        sql: SQL 查询语句
        limit: 结果行数限制，默认100行。设置为0则不限制（谨慎使用）

    Returns:
        JSON格式字符串，包含：
        - success: bool
        - row_count: int
        - columns: list
        - data: list[dict] 查询结果数据
        - error: str (仅失败时)

    Examples:
        # 聚合统计
        execute_sql_query("SELECT status, COUNT(*) as cnt FROM orders WHERE ETL_DATE='2025-09-30' GROUP BY status")

        # 小数据集查询
        execute_sql_query("SELECT * FROM users WHERE ETL_DATE='2025-09-30' AND age > 60", limit=50)

        # 数据质量检查
        execute_sql_query("SELECT COUNT(*) as null_count FROM users WHERE email IS NULL AND ETL_DATE='2025-09-30'")
    """
    # 直接调用 sql_query，固定 save_to_file=False
    return sql_query(
        sql=sql,
        runtime=runtime,
        limit=limit,
        save_to_file=False,
        file_description=None
    )
