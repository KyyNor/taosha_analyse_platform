"""
指标数据查询服务
"""

from typing import List, Dict, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from datetime import datetime, timedelta
import duckdb
import pandas as pd
from pathlib import Path
import json

from models.fraudhunter.indicator import FraudHunterIndicatorDefinition
from models.fraudhunter.wide_table import (
    FraudHunterWideTableVersion,
    FraudHunterWideTableSnapshot
)
from utils.logger import logger
from utils.config import settings


class DataQueryService:
    """数据查询服务"""

    # 对象类型到宽表名称的映射
    OBJECT_TYPE_TO_TABLE_NAME = {
        'cust_no': 'cust_wide_table',
        'dep_acct_no': 'dep_acct_wide_table',
        'loan_acct_no': 'loan_acct_wide_table',
    }

    # 宽表名称到对象类型的映射
    TABLE_NAME_TO_OBJECT_TYPE = {
        'cust_wide_table': 'cust_no',
        'dep_acct_wide_table': 'dep_acct_no',
        'loan_acct_wide_table': 'loan_acct_no',
    }

    def __init__(self, db: Session):
        self.db = db

    def get_wide_table_files(
        self,
        object_type: str,
        date_filter: Optional[str] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Dict[str, Any]:
        """获取宽表文件列表

        Args:
            object_type: 对象类型
            date_filter: 日期过滤，格式: YYYY-MM-DD
            page: 页码
            page_size: 每页大小

        Returns:
            包含文件列表和分页信息的字典
        """
        wide_table_name = self.OBJECT_TYPE_TO_TABLE_NAME.get(object_type)
        if not wide_table_name:
            raise ValueError(f"不支持的对象类型: {object_type}")

        # 构建基础查询
        query = self.db.query(FraudHunterWideTableSnapshot).filter(
            FraudHunterWideTableSnapshot.wide_table_name == wide_table_name,
            FraudHunterWideTableSnapshot.status == 'ready'
        )

        # 日期过滤
        if date_filter:
            try:
                filter_date = datetime.strptime(date_filter, "%Y-%m-%d").date()
                query = query.filter(FraudHunterWideTableSnapshot.etl_date == filter_date)
            except ValueError:
                raise ValueError(f"日期格式错误: {date_filter}，应为 YYYY-MM-DD")

        # 按时间倒序排列
        query = query.order_by(desc(FraudHunterWideTableSnapshot.etl_date))

        # 分页
        total = query.count()
        snapshots = query.offset((page - 1) * page_size).limit(page_size).all()

        # 转换为响应格式
        files = []
        for snapshot in snapshots:
            files.append({
                "id": snapshot.id,
                "wide_table_name": snapshot.wide_table_name,
                "etl_date": snapshot.etl_date,
                "version_hash": snapshot.version_hash,
                "file_path": snapshot.parquet_file_path,
                "status": snapshot.status,
                "generation_time": snapshot.generation_time,
                "row_count": snapshot.row_count,
                "column_count": snapshot.column_count,
                "file_size_bytes": snapshot.file_size_bytes,
                "is_realtime": snapshot.version_hash is None
            })

        return {
            "items": files,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }

    def get_indicators_by_wide_table(self, snapshot_id: int) -> List[Dict[str, Any]]:
        """根据宽表快照获取指标信息

        Args:
            snapshot_id: 快照ID

        Returns:
            指标信息列表
        """
        # 获取快照信息
        snapshot = self.db.query(FraudHunterWideTableSnapshot).get(snapshot_id)
        if not snapshot:
            raise ValueError(f"未找到快照 ID={snapshot_id}")

        if snapshot.version_hash:
            # 离线宽表：从版本信息获取指标
            version = self.db.query(FraudHunterWideTableVersion).filter(
                FraudHunterWideTableVersion.version_hash == snapshot.version_hash
            ).first()

            if not version:
                raise ValueError(f"未找到版本信息 version_hash={snapshot.version_hash}")

            indicator_metadata = version.indicator_metadata or {}
            indicator_ids = list(indicator_metadata.keys())
        else:
            # 实时宽表：获取当前current版本的指标
            current_version = self.db.query(FraudHunterWideTableVersion).filter(
                FraudHunterWideTableVersion.wide_table_name == snapshot.wide_table_name,
                FraudHunterWideTableVersion.status == 'current'
            ).first()

            if current_version:
                indicator_metadata = current_version.indicator_metadata or {}
                indicator_ids = list(indicator_metadata.keys())
            else:
                # 如果没有current版本，查询所有上线的指标
                object_type = self.TABLE_NAME_TO_OBJECT_TYPE.get(snapshot.wide_table_name)
                indicators = self.db.query(FraudHunterIndicatorDefinition).filter(
                    FraudHunterIndicatorDefinition.object_type == object_type,
                    FraudHunterIndicatorDefinition.status == 'online'
                ).all()
                indicator_ids = [ind.id for ind in indicators]

        if not indicator_ids:
            return []

        # 查询指标详细信息
        indicators = self.db.query(FraudHunterIndicatorDefinition).filter(
            FraudHunterIndicatorDefinition.id.in_(indicator_ids)
        ).all()

        # 添加target_id字段
        result = [
            {
                "id": 0,
                "indicator_code": "target_id",
                "indicator_name": "对象ID",
                "indicator_type": "system",
                "data_type": "string",
                "object_type": self.TABLE_NAME_TO_OBJECT_TYPE.get(snapshot.wide_table_name)
            }
        ]

        # 添加指标字段
        for ind in indicators:
            result.append({
                "id": ind.id,
                "indicator_code": ind.indicator_code,
                "indicator_name": ind.indicator_name,
                "indicator_type": ind.indicator_type,
                "data_type": ind.data_type,
                "object_type": ind.object_type
            })

        return result

    def query_data(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """查询宽表数据

        Args:
            request: 查询请求

        Returns:
            查询结果
        """
        try:
            # 1. 获取快照信息
            snapshot = self.db.query(FraudHunterWideTableSnapshot).get(request["snapshot_id"])
            if not snapshot:
                raise ValueError(f"未找到快照 ID={request['snapshot_id']}")

            if snapshot.status != 'ready':
                raise ValueError(f"快照状态不是ready，当前状态: {snapshot.status}")

            # 2. 检查文件是否存在
            file_path = Path(snapshot.parquet_file_path)
            if not file_path.exists():
                raise ValueError(f"文件不存在: {snapshot.parquet_file_path}")

            # 3. 构建SQL查询
            sql_query = self._build_query_sql(request)
            count_sql = self._build_count_sql(request)

            # 4. 执行查询
            con = duckdb.connect(database=':memory:')

            # 加载Parquet文件
            con.execute(f"CREATE TABLE wide_table AS SELECT * FROM read_parquet('{snapshot.parquet_file_path}')")

            # 获取总数
            total_result = con.execute(count_sql).fetchone()
            total_count = total_result[0] if total_result else 0

            # 执行分页查询
            if total_count > 0:
                result_df = con.execute(sql_query).fetchdf()
                items = result_df.to_dict('records')
            else:
                items = []

            con.close()

            # 5. 格式化结果
            return {
                "items": items,
                "total": total_count,
                "page": request.get("page", 1),
                "page_size": request.get("page_size", 100)
            }

        except Exception as e:
            logger.error(f"查询数据失败: {str(e)}")
            raise

    def _build_query_sql(self, request: Dict[str, Any]) -> str:
        """构建查询SQL"""
        # 基础SELECT - 查询所有字段
        base_sql = "SELECT * FROM wide_table WHERE 1=1"

        # 添加target_id条件
        if request.get("target_id"):
            base_sql += f" AND target_id = '{request['target_id']}'"

        # 添加指标查询条件
        conditions = request.get("conditions", [])
        for condition in conditions:
            field = condition["field"]
            operator = condition["operator"]
            value = condition["value"]

            # 跳过target_id的条件，因为已经单独处理
            if field == "target_id":
                continue

            if operator == "like":
                base_sql += f" AND {field} LIKE '%{value}%'"
            elif operator == "=":
                if isinstance(value, str):
                    base_sql += f" AND {field} = '{value}'"
                else:
                    base_sql += f" AND {field} = {value}"
            elif operator in [">", "<", ">=", "<="]:
                if isinstance(value, str):
                    # 尝试转换为数值
                    try:
                        value = float(value)
                        base_sql += f" AND {field} {operator} {value}"
                    except ValueError:
                        # 如果不能转换为数值，作为字符串比较
                        base_sql += f" AND CAST({field} AS VARCHAR) {operator} '{value}'"
                else:
                    base_sql += f" AND {field} {operator} {value}"

        # 添加分页
        page = request.get("page", 1)
        page_size = request.get("page_size", 100)
        offset = (page - 1) * page_size
        base_sql += f" LIMIT {page_size} OFFSET {offset}"

        return base_sql

    def _build_count_sql(self, request: Dict[str, Any]) -> str:
        """构建计数SQL"""
        base_sql = "SELECT COUNT(*) FROM wide_table WHERE 1=1"

        # 添加target_id条件
        if request.get("target_id"):
            base_sql += f" AND target_id = '{request['target_id']}'"

        # 添加指标查询条件（不分页）
        conditions = request.get("conditions", [])
        for condition in conditions:
            field = condition["field"]
            operator = condition["operator"]
            value = condition["value"]

            # 跳过target_id的条件
            if field == "target_id":
                continue

            if operator == "like":
                base_sql += f" AND {field} LIKE '%{value}%'"
            elif operator == "=":
                if isinstance(value, str):
                    base_sql += f" AND {field} = '{value}'"
                else:
                    base_sql += f" AND {field} = {value}"
            elif operator in [">", "<", ">=", "<="]:
                if isinstance(value, str):
                    try:
                        value = float(value)
                        base_sql += f" AND {field} {operator} {value}"
                    except ValueError:
                        base_sql += f" AND CAST({field} AS VARCHAR) {operator} '{value}'"
                else:
                    base_sql += f" AND {field} {operator} {value}"

        return base_sql