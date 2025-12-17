"""
指标数据查询服务
"""

from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime
import duckdb
from pathlib import Path

from models.fraudhunter.indicator import FraudHunterIndicatorDefinition
from models.fraudhunter.wide_table import (
    FraudHunterWideTableVersion,
    FraudHunterWideTableSnapshot
)
from utils.logger import logger


class IndicatorQueryService:
    """指标数据查询服务"""

    # 宽表类型配置
    # key: 前端选择的宽表类型
    # value: {wide_table_name: 数据库中的宽表名称, label: 显示名称, is_realtime: 是否实时宽表}
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

    def __init__(self, db: Session):
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
        config = self.WIDE_TABLE_CONFIG.get(wide_table_type)
        if not config:
            raise ValueError(f"不支持的宽表类型: {wide_table_type}")

        wide_table_name = config['wide_table_name']
        is_realtime = config['is_realtime']

        # 构建基础查询 - 从 FraudHunterWideTableSnapshot 获取
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

        # 获取版本信息（离线宽表需要）
        version_info_map = {}
        if not is_realtime:
            # 获取所有相关的版本信息
            version_hashes = [s.version_hash for s in snapshots if s.version_hash]
            if version_hashes:
                versions = self.db.query(FraudHunterWideTableVersion).filter(
                    FraudHunterWideTableVersion.version_hash.in_(version_hashes)
                ).all()
                version_info_map = {v.version_hash: v for v in versions}

        # 转换为响应格式
        files = []
        for snapshot in snapshots:
            # 获取版本状态
            version_status = None
            if snapshot.version_hash and snapshot.version_hash in version_info_map:
                version_status = version_info_map[snapshot.version_hash].status

            # 构建显示标签: 数据日期(版本号[状态])
            etl_date_str = snapshot.etl_date.strftime('%Y-%m-%d') if snapshot.etl_date else ''
            if snapshot.version_hash:
                version_short = snapshot.version_hash[:6] if snapshot.version_hash else ''
                display_label = f"{etl_date_str}({version_short}[{version_status or 'unknown'}])"
            else:
                display_label = f"{etl_date_str}(实时)"

            # 获取文件名
            file_name = Path(snapshot.parquet_file_path).name if snapshot.parquet_file_path else ''

            files.append({
                "id": snapshot.id,
                "wide_table_name": snapshot.wide_table_name,
                "etl_date": snapshot.etl_date,
                "version_hash": snapshot.version_hash,
                "version_status": version_status,
                "file_path": snapshot.parquet_file_path,
                "file_name": file_name,
                "display_label": display_label,
                "status": snapshot.status,
                "generation_time": snapshot.generation_time,
                "row_count": snapshot.row_count,
                "column_count": snapshot.column_count,
                "file_size_bytes": snapshot.file_size_bytes,
                "is_realtime": is_realtime
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

            parquet_path = snapshot.parquet_file_path

            # 3. 获取指标信息用于构建SELECT字段和类型转换
            indicators = self.get_indicators_by_wide_table(snapshot.id)
            indicator_map = {ind['indicator_code']: ind for ind in indicators}

            # 4. 构建SQL查询
            sql_query = self._build_query_sql(request, parquet_path, indicator_map)
            count_sql = self._build_count_sql(request, parquet_path)

            logger.info(f"执行查询SQL: {sql_query[:500]}...")

            # 5. 执行查询
            con = duckdb.connect(database=':memory:')

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

            # 6. 格式化结果
            return {
                "items": items,
                "total": total_count,
                "page": request.get("page", 1),
                "page_size": request.get("page_size", 100)
            }

        except Exception as e:
            logger.error(f"查询数据失败: {str(e)}")
            raise

    def _get_cast_expression(self, field: str, data_type: str) -> str:
        """根据数据类型获取CAST表达式

        Args:
            field: 字段名
            data_type: 数据类型 (string, numeric, date)

        Returns:
            CAST表达式
        """
        if data_type == 'numeric':
            return f"CAST({field} AS DOUBLE)"
        elif data_type == 'date':
            return f"CAST({field} AS DATE)"
        else:
            # string 或其他类型
            return f"CAST({field} AS VARCHAR)"

    def _build_query_sql(
        self,
        request: Dict[str, Any],
        parquet_path: str,
        indicator_map: Dict[str, Dict]
    ) -> str:
        """构建查询SQL - 直接从parquet文件查询，带中文别名

        Args:
            request: 查询请求
            parquet_path: parquet文件路径
            indicator_map: 指标信息映射 {indicator_code: indicator_info}

        Returns:
            SQL查询语句
        """
        # 构建SELECT字段 - 使用中文别名，并根据类型CAST
        select_fields = []

        # 添加target_id字段
        select_fields.append('target_id AS "对象ID"')
        select_fields.append('etl_date AS "数据日期"')

        # 添加指标字段 - 按中文名称展示，并根据类型CAST
        for code, info in indicator_map.items():
            if code in ('target_id', 'etl_date'):
                continue
            indicator_name = info.get('indicator_name', code)
            data_type = info.get('data_type', 'string')

            # 根据数据类型进行CAST
            cast_expr = self._get_cast_expression(code, data_type)
            select_fields.append(f'{cast_expr} AS "{indicator_name}"')

        select_clause = ",\n    ".join(select_fields)

        # 构建WHERE子句
        where_conditions = ["1=1"]

        # 添加target_id条件
        if request.get("target_id"):
            target_id = request['target_id'].replace("'", "''")  # 防SQL注入
            where_conditions.append(f"target_id = '{target_id}'")

        # 添加指标查询条件
        conditions = request.get("conditions", [])
        for condition in conditions:
            field = condition["field"]
            operator = condition["operator"]
            value = condition["value"]

            # 跳过target_id的条件，因为已经单独处理
            if field == "target_id":
                continue

            # 获取指标的数据类型
            indicator_info = indicator_map.get(field, {})
            data_type = indicator_info.get('data_type', 'string')

            # 根据数据类型构建条件
            condition_sql = self._build_condition(field, operator, value, data_type)
            if condition_sql:
                where_conditions.append(condition_sql)

        where_clause = " AND ".join(where_conditions)

        # 添加分页
        page = request.get("page", 1)
        page_size = request.get("page_size", 100)
        offset = (page - 1) * page_size

        # 构建完整SQL - 直接从parquet文件查询
        sql = f"""SELECT
    {select_clause}
FROM read_parquet('{parquet_path}')
WHERE {where_clause}
LIMIT {page_size} OFFSET {offset}"""

        return sql

    def _build_condition(
        self,
        field: str,
        operator: str,
        value: Any,
        data_type: str
    ) -> str:
        """构建单个查询条件

        Args:
            field: 字段名
            operator: 运算符
            value: 值
            data_type: 数据类型 (numeric/text/date)

        Returns:
            SQL条件表达式
        """
        if not value and value != 0:
            return ""

        # 防SQL注入
        if isinstance(value, str):
            value = value.replace("'", "''")

        if operator == "like":
            return f"{field} LIKE '%{value}%'"
        elif operator == "=":
            if data_type == 'numeric':
                try:
                    num_value = float(value)
                    return f"{field} = {num_value}"
                except (ValueError, TypeError):
                    return f"CAST({field} AS VARCHAR) = '{value}'"
            else:
                return f"{field} = '{value}'"
        elif operator in [">", "<", ">=", "<="]:
            if data_type == 'numeric':
                try:
                    num_value = float(value)
                    return f"{field} {operator} {num_value}"
                except (ValueError, TypeError):
                    return f"CAST({field} AS VARCHAR) {operator} '{value}'"
            elif data_type == 'date':
                return f"{field} {operator} '{value}'"
            else:
                return f"CAST({field} AS VARCHAR) {operator} '{value}'"

        return ""

    def _build_count_sql(self, request: Dict[str, Any], parquet_path: str) -> str:
        """构建计数SQL - 直接从parquet文件查询

        Args:
            request: 查询请求
            parquet_path: parquet文件路径

        Returns:
            SQL计数语句
        """
        # 构建WHERE子句
        where_conditions = ["1=1"]

        # 添加target_id条件
        if request.get("target_id"):
            target_id = request['target_id'].replace("'", "''")
            where_conditions.append(f"target_id = '{target_id}'")

        # 添加指标查询条件
        conditions = request.get("conditions", [])
        for condition in conditions:
            field = condition["field"]
            operator = condition["operator"]
            value = condition["value"]

            if field == "target_id":
                continue

            # 简化的条件构建（计数不需要类型转换）
            if not value and value != 0:
                continue

            if isinstance(value, str):
                value = value.replace("'", "''")

            if operator == "like":
                where_conditions.append(f"{field} LIKE '%{value}%'")
            elif operator == "=":
                if isinstance(value, (int, float)):
                    where_conditions.append(f"{field} = {value}")
                else:
                    try:
                        num_value = float(value)
                        where_conditions.append(f"{field} = {num_value}")
                    except (ValueError, TypeError):
                        where_conditions.append(f"{field} = '{value}'")
            elif operator in [">", "<", ">=", "<="]:
                try:
                    num_value = float(value)
                    where_conditions.append(f"{field} {operator} {num_value}")
                except (ValueError, TypeError):
                    where_conditions.append(f"CAST({field} AS VARCHAR) {operator} '{value}'")

        where_clause = " AND ".join(where_conditions)

        return f"SELECT COUNT(*) FROM read_parquet('{parquet_path}') WHERE {where_clause}"