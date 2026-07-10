"""
指标数据查询服务
"""

from typing import List, Dict, Optional, Any
from datetime import date

import numpy as np
import pandas as pd
from pandas._libs.tslibs.nattype import NaTType
from sqlalchemy import desc, and_
from sqlalchemy.orm import Session

from models.fraudhunter.indicator import FraudHunterIndicatorDefinition
from models.fraudhunter.wide_table import (
    FraudHunterWideTableVersion,
    FraudHunterWideTableSnapshot
)
from utils.logger import logger
from utils.analyze_db_utils import AnalyzeDBConnector

# 宽表类型配置
WIDE_TABLE_CONFIG = {
    'dep_acct_offline': {
        'wide_table_name': 'dep_acct_wide_table',
        'label': '离线存款宽表',
        'is_realtime': False,
        'object_type': 'dep_acct_no'
    },
    'loan_acct_offline': {
        'wide_table_name': 'loan_acct_wide_table',
        'label': '离线贷款宽表',
        'is_realtime': False,
        'object_type': 'loan_acct_no'
    },
    'cust_offline': {
        'wide_table_name': 'cust_wide_table',
        'label': '离线客户宽表',
        'is_realtime': False,
        'object_type': 'cust_no'
    },
    'dep_acct_realtime': {
        'wide_table_name': 'dep_acct_wide_table_realtime',
        'label': '实时存款宽表',
        'is_realtime': True,
        'object_type': 'dep_acct_no'
    }
}

# 宽表名称到对象类型的映射
TABLE_NAME_TO_OBJECT_TYPE = {
    'cust_wide_table': 'cust_no',
    'dep_acct_wide_table': 'dep_acct_no',
    'loan_acct_wide_table': 'loan_acct_no',
    'dep_acct_wide_table_realtime': 'dep_acct_no'
}


class IndicatorQueryService:
    """指标数据查询服务"""

    def __init__(self, db: Session) -> None:
        """初始化查询服务

        Args:
            db: 数据库会话
        """
        self.db = db

    def get_wide_table_files(
        self,
        wide_table_type: str,
        date_filter: Optional[str] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Dict[str, Any]:
        """获取宽表文件列表

        Args:
            wide_table_type: 宽表类型 (dep_acct_offline, loan_acct_offline, cust_offline, dep_acct_realtime)
            date_filter: 日期过滤，格式: YYYY-MM-DD
            page: 页码
            page_size: 每页大小

        Returns:
            包含文件列表和分页信息的字典
        """
        config = WIDE_TABLE_CONFIG.get(wide_table_type)
        if not config:
            raise ValueError(f"不支持的宽表类型: {wide_table_type}")

        wide_table_name = config['wide_table_name']
        is_realtime = config['is_realtime']

        # 构建基础查询
        query = self.db.query(FraudHunterWideTableSnapshot).filter(
            FraudHunterWideTableSnapshot.wide_table_name == wide_table_name,
            FraudHunterWideTableSnapshot.status == 'ready'
        )

        # 日期过滤
        if date_filter:
            from datetime import datetime
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

        # 获取版本信息（离线宽表需要）
        version_info_map = self._get_version_info_map(snapshots) if not is_realtime else {}

        # 转换为响应格式
        files = [
            self._snapshot_to_file_dict(s, version_info_map, is_realtime)
            for s in snapshots
        ]

        return {
            "items": files,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }

    def _get_version_info_map(self, snapshots: List[FraudHunterWideTableSnapshot]) -> Dict[str, FraudHunterWideTableVersion]:
        """获取快照对应的版本信息映射"""
        version_hashes = [s.version_hash for s in snapshots if s.version_hash]
        if not version_hashes:
            return {}

        versions = self.db.query(FraudHunterWideTableVersion).filter(
            FraudHunterWideTableVersion.version_hash.in_(version_hashes)
        ).all()
        return {v.version_hash: v for v in versions}

    def _snapshot_to_file_dict(
        self,
        snapshot: FraudHunterWideTableSnapshot,
        version_info_map: Dict[str, FraudHunterWideTableVersion],
        is_realtime: bool
    ) -> Dict[str, Any]:
        """将快照转换为文件字典"""
        version_status = None
        if snapshot.version_hash and snapshot.version_hash in version_info_map:
            version_status = version_info_map[snapshot.version_hash].status

        # 构建显示标签: 数据日期(版本号[状态])
        etl_date_str = snapshot.etl_date.strftime('%Y-%m-%d') if snapshot.etl_date else ''
        if snapshot.version_hash:
            version_short = snapshot.version_hash[:6]
            display_label = f"{etl_date_str}({version_short}[{version_status or 'unknown'}])"
        else:
            display_label = f"{etl_date_str}(实时)"

        return {
            "id": snapshot.id,
            "wide_table_name": snapshot.wide_table_name,
            "etl_date": snapshot.etl_date,
            "version_hash": snapshot.version_hash,
            "version_status": version_status,
            "file_path": snapshot.parquet_file_path,
            "file_name": snapshot.parquet_file_path or '',
            "display_label": display_label,
            "status": snapshot.status,
            "generation_time": snapshot.generation_time,
            "row_count": snapshot.row_count,
            "column_count": snapshot.column_count,
            "file_size_bytes": snapshot.file_size_bytes,
            "is_realtime": is_realtime
        }

    def get_indicators_by_wide_table(self, snapshot_id: int) -> List[Dict[str, Any]]:
        """根据宽表快照获取指标信息

        Args:
            snapshot_id: 快照ID

        Returns:
            指标信息列表
        """
        snapshot = self.db.query(FraudHunterWideTableSnapshot).get(snapshot_id)
        if not snapshot:
            raise ValueError(f"未找到快照 ID={snapshot_id}")

        indicator_ids = self._get_indicator_ids(snapshot)
        if not indicator_ids:
            return []

        indicators = self.db.query(FraudHunterIndicatorDefinition).filter(
            FraudHunterIndicatorDefinition.id.in_(indicator_ids)
        ).all()

        result = [self._create_target_id_field(snapshot)]
        result.extend(self._indicator_to_dict(ind) for ind in indicators)
        return result

    def _get_indicator_ids(self, snapshot: FraudHunterWideTableSnapshot) -> List[int]:
        """获取快照对应的指标ID列表"""
        if snapshot.version_hash:
            # 离线宽表：从版本信息获取指标
            version = self.db.query(FraudHunterWideTableVersion).filter(
                FraudHunterWideTableVersion.version_hash == snapshot.version_hash
            ).first()

            if not version:
                raise ValueError(f"未找到版本信息 version_hash={snapshot.version_hash}")

            indicator_metadata = version.indicator_metadata or {}
            return list(indicator_metadata.keys())
        else:
            # 实时宽表：获取current版本的指标
            current_version = self.db.query(FraudHunterWideTableVersion).filter(
                FraudHunterWideTableVersion.wide_table_name == snapshot.wide_table_name,
                FraudHunterWideTableVersion.status == 'current'
            ).first()

            if current_version:
                indicator_metadata = current_version.indicator_metadata or {}
                return list(indicator_metadata.keys())
            else:
                # 查询所有上线的指标
                object_type = TABLE_NAME_TO_OBJECT_TYPE.get(snapshot.wide_table_name)
                indicators = self.db.query(FraudHunterIndicatorDefinition).filter(
                    FraudHunterIndicatorDefinition.object_type == object_type,
                    FraudHunterIndicatorDefinition.status == 'online'
                ).all()
                return [ind.id for ind in indicators]

    def _create_target_id_field(self, snapshot: FraudHunterWideTableSnapshot) -> Dict[str, Any]:
        """创建target_id字段"""
        return {
            "id": 0,
            "indicator_code": "target_id",
            "indicator_name": "对象ID",
            "indicator_type": "system",
            "data_type": "string",
            "object_type": TABLE_NAME_TO_OBJECT_TYPE.get(snapshot.wide_table_name)
        }

    @staticmethod
    def _indicator_to_dict(indicator: FraudHunterIndicatorDefinition) -> Dict[str, Any]:
        """将指标转换为字典"""
        return {
            "id": indicator.id,
            "indicator_code": indicator.indicator_code,
            "indicator_name": indicator.indicator_name,
            "indicator_type": indicator.indicator_type,
            "data_type": indicator.data_type,
            "object_type": indicator.object_type
        }

    def query_data(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """查询宽表数据

        Args:
            request: 查询请求

        Returns:
            查询结果
        """
        try:
            snapshot = self.db.query(FraudHunterWideTableSnapshot).get(request["snapshot_id"])
            if not snapshot:
                raise ValueError(f"未找到快照 ID={request['snapshot_id']}")

            if snapshot.status != 'ready':
                raise ValueError(f"快照状态不是ready，当前状态: {snapshot.status}")

            pg_table_name = snapshot.parquet_file_path
            if not pg_table_name:
                raise ValueError(f"快照未关联PG表: snapshot_id={request['snapshot_id']}")

            indicators = self.get_indicators_by_wide_table(snapshot.id)
            indicator_map = {ind['indicator_code']: ind for ind in indicators}

            sql_query = self._build_query_sql(request, pg_table_name, snapshot.etl_date, indicator_map)
            count_sql = self._build_count_sql(request, pg_table_name, snapshot.etl_date)

            logger.info(f"执行查询SQL: {sql_query[:500]}...")

            # 获取总数
            total_df = AnalyzeDBConnector.execute_sql(count_sql, fetch_df=True)
            total_count = int(total_df.iloc[0]['count']) if total_df is not None and not total_df.empty else 0

            # 执行分页查询
            if total_count > 0:
                result_df = AnalyzeDBConnector.execute_sql(sql_query, fetch_df=True)
                items = self._convert_numpy_types(result_df.to_dict('records')) if result_df is not None else []
            else:
                items = []

            return {
                "items": items,
                "total": int(total_count),
                "page": request.get("page", 1),
                "page_size": request.get("page_size", 100)
            }

        except Exception as e:
            logger.error(f"查询数据失败: {str(e)}", exc_info=True)
            raise

    @staticmethod
    def _get_cast_expression(field: str, data_type: str) -> str:
        """根据数据类型获取CAST表达式"""
        if data_type == 'numeric':
            return f"COALESCE({field}::DOUBLE PRECISION, 0)"
        elif data_type == 'date':
            return f"CAST(NULLIF({field}, '') AS DATE)"
        else:
            return f"CAST({field} AS VARCHAR)"

    def _build_query_sql(
        self,
        request: Dict[str, Any],
        pg_table_name: str,
        etl_date: date,
        indicator_map: Dict[str, Dict]
    ) -> str:
        """构建查询SQL"""
        select_fields = ['target_id AS "对象ID"', 'etl_date AS "数据日期"']

        # 添加指标字段
        for code, info in indicator_map.items():
            if code in ('target_id', 'etl_date'):
                continue
            indicator_name = info.get('indicator_name', code)
            data_type = info.get('data_type', 'string')
            cast_expr = self._get_cast_expression(code, data_type)
            select_fields.append(f'{cast_expr} AS "{indicator_name}"')

        select_clause = ",\n    ".join(select_fields)
        where_clause = self._build_where_clause(request, indicator_map, etl_date)

        page = request.get("page", 1)
        page_size = request.get("page_size", 100)
        offset = (page - 1) * page_size

        return f'''SELECT
    {select_clause}
FROM {pg_table_name}
WHERE {where_clause}
LIMIT {page_size} OFFSET {offset}'''

    def _build_where_clause(
        self,
        request: Dict[str, Any],
        indicator_map: Dict[str, Dict],
        etl_date: date
    ) -> str:
        """构建WHERE子句"""
        where_conditions = [f"etl_date = '{etl_date}'"]

        # 添加target_id条件
        if request.get("target_id"):
            target_id = request['target_id'].replace("'", "''")
            where_conditions.append(f"target_id = '{target_id}'")

        # 添加指标查询条件
        for condition in request.get("conditions", []):
            field = condition["field"]
            operator = condition["operator"]
            value = condition["value"]

            if field == "target_id":
                continue

            indicator_info = indicator_map.get(field, {})
            data_type = indicator_info.get('data_type', 'string')
            condition_sql = self._build_condition(field, operator, value, data_type)
            if condition_sql:
                where_conditions.append(condition_sql)

        return " AND ".join(where_conditions)

    @staticmethod
    def _build_condition(field: str, operator: str, value: Any, data_type: str) -> str:
        """构建单个查询条件"""
        if not value and value != 0:
            return ""

        if isinstance(value, str):
            value = value.replace("'", "''")

        if operator == "like":
            return f"{field} LIKE '%{value}%'"
        elif operator == "=":
            if data_type == 'numeric':
                try:
                    return f"COALESCE({field}::DOUBLE PRECISION, 0) = {float(value)}"
                except (ValueError, TypeError):
                    return f"CAST({field} AS VARCHAR) = '{value}'"
            else:
                return f"{field} = '{value}'"
        elif operator in [">", "<", ">=", "<="]:
            if data_type == 'numeric':
                try:
                    return f"COALESCE({field}::DOUBLE PRECISION, 0) {operator} {float(value)}"
                except (ValueError, TypeError):
                    return f"CAST({field} AS VARCHAR) {operator} '{value}'"
            elif data_type == 'date':
                return f"NULLIF({field}, '') {operator} '{value}'"
            else:
                return f"CAST({field} AS VARCHAR) {operator} '{value}'"

        return ""

    def _build_count_sql(
        self,
        request: Dict[str, Any],
        pg_table_name: str,
        etl_date: date
    ) -> str:
        """构建计数SQL"""
        where_conditions = [f"etl_date = '{etl_date}'"]

        if request.get("target_id"):
            target_id = request['target_id'].replace("'", "''")
            where_conditions.append(f"target_id = '{target_id}'")

        # 添加指标查询条件（简化版，不需要类型转换）
        for condition in request.get("conditions", []):
            field = condition["field"]
            operator = condition["operator"]
            value = condition["value"]

            if field == "target_id" or (not value and value != 0):
                continue

            if isinstance(value, str):
                value = value.replace("'", "''")

            if operator == "like":
                where_conditions.append(f"{field} LIKE '%{value}%'")
            elif operator == "=":
                try:
                    where_conditions.append(f"{field} = {float(value)}")
                except (ValueError, TypeError):
                    where_conditions.append(f"{field} = '{value}'")
            elif operator in [">", "<", ">=", "<="]:
                try:
                    where_conditions.append(f"{field} {operator} {float(value)}")
                except (ValueError, TypeError):
                    where_conditions.append(f"CAST({field} AS VARCHAR) {operator} '{value}'")

        where_clause = " AND ".join(where_conditions)
        return f'SELECT COUNT(*) AS count FROM {pg_table_name} WHERE {where_clause}'

    @staticmethod
    def _convert_numpy_types(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """将numpy/pandas类型转换成原生python类型"""
        def convert_value(val):
            if val is None or (isinstance(val, float) and np.isnan(val)):
                return None
            if isinstance(val, (np.integer, np.int64, np.int32)):
                return int(val)
            if isinstance(val, (np.floating, np.float64, np.float32)):
                return float(val)
            if isinstance(val, np.bool_):
                return bool(val)
            if isinstance(val, (np.ndarray, list)):
                return [convert_value(v) for v in val]
            if isinstance(val, (pd.Timestamp, np.datetime64)):
                return str(val)
            if isinstance(val, bytes):
                return val.decode('utf-8', errors='replace')
            if isinstance(val, NaTType):
                return None
            return val

        return [{k: convert_value(v) for k, v in record.items()} for record in records]