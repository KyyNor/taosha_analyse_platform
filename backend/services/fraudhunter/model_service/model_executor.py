"""
模型历史回测执行器

负责执行模型的历史回测任务，生成SQL并按日执行

版本选择策略:
- 直接使用指定日期的最新版本宽表（根据版本创建时间排序）
- 不考虑current/target状态
- 不检查指标版本匹配
"""

import asyncio
import json
import math
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from models.db_base import get_db_session
from models.fraudhunter.risk_control_model import FraudHunterModelDefinition
from models.fraudhunter.wide_table import (
    FraudHunterWideTableVersion,
    FraudHunterWideTableSnapshot
)
from models.fraudhunter.dry_run_task import FraudHunterDryRunExecution
from schemas.fraudhunter.rule import RuleConfig
from services.fraudhunter.model_service.rule_engine import RuleEngine
from services.fraudhunter.system_config_service import SystemConfigManager
from services.fraudhunter.wide_table_service.store import query_router
from services.fraudhunter.wide_table_service.store.query_router import get_query_session
from utils.config import settings


# =============================================================================
# 公共工具：构建模型白名单字典（key = model.id 整数）
# config 格式: [{'模型ID': <int/str>, '白名单账号': '<str>'}, ...]
# 返回    : {model_id(int): [account_id(str), ...]}
# =============================================================================

def build_model_whitelist_dict(
    config_list: list,
) -> dict[int, list[str]]:
    """
    将系统配置中的模型白名单列表，转换为以 model.id（整数）为 key 的字典。

    示例
    -----
    >>> raw = [{'模型ID': 55, '白名单账号': 'acc1'}, {'模型ID': 32, '白名单账号': 'acc2'}]
    >>> build_model_whitelist_dict(raw)  # → {55: ['acc1'], 32: ['acc2']}

    配置值可为整数（直接使用）或字符串（如从 YAML 反序列化后的 '55'），本方法统一做 int 转换，
    与 FraudHunterModelDefinition.id 的 Integer 类型对齐，保证字典查询不走空。
    """
    result: dict[int, list[str]] = {}
    for item in config_list:
        model_id_str = item.get('模型ID', '')
        account_id = item.get('白名单账号', '')
        try:
            model_id: int = int(model_id_str)
        except (TypeError, ValueError):
            continue  # 配置项格式错误（如空字典 / 非数字值），静默跳过
        if model_id and account_id:
            result.setdefault(model_id, []).append(str(account_id))
    return result
from utils.logger import logger
from utils.analyze_db_utils import AnalyzeDBConnector

# 对象类型到宽表名称的映射
OBJECT_TYPE_TO_WIDE_TABLE = {
    'dep_acct_no': 'dep_acct_wide_table',
    'cust_no': 'cust_wide_table',
    'loan_acct_no': 'loan_acct_wide_table'
}


@dataclass
class VersionSelectionResult:
    """版本选择结果"""
    version_hash: str
    wide_table_name: str
    etl_date: date
    parquet_path: Optional[str]
    message: str = ""
    storage_backend: str = 'postgresql'

    @property
    def pg_table_name(self) -> Optional[str]:
        """获取PG表名"""
        if self.wide_table_name and self.version_hash and self.etl_date:
            return f"{self.wide_table_name}_{self.version_hash}_{self.etl_date.strftime('%Y%m%d')}"
        else:
            return None


class ModelExecutor:
    """模型执行器 - 历史回测专用"""

    def __init__(self) -> None:
        """初始化执行器"""
        pass

    @staticmethod
    def get_wide_table_name(object_type: str) -> str:
        """获取宽表名称

        Args:
            object_type: 对象类型

        Returns:
            宽表名称
        """
        return OBJECT_TYPE_TO_WIDE_TABLE.get(object_type, 'dep_acct_wide_table')

    @staticmethod
    def _build_cust_realtime_join_clause(cust_realtime_table_name: Optional[str]) -> List[str]:
        """构建客户实时宽表 LEFT JOIN 的 SQL 行（与回测现有 cust_offline JOIN 同风格、同关联键）。

        关联键：存款实时宽表的客户号外键列 i_dep_acct_no_offline_00001
        = 客户实时宽表 target_id（与 cust_offline JOIN 完全平行）。

        Args:
            cust_realtime_table_name: 当天客户宽表 PG 表名；为空则不生成 JOIN。

        Returns:
            JOIN 子句的 SQL 行列表；无表名(None/空串/纯空白)时返回空列表（不 JOIN）。
        """
        if not cust_realtime_table_name or not cust_realtime_table_name.strip():
            return []
        return [
            "LEFT JOIN",
            f"    {cust_realtime_table_name} as cust_realtime_indicator",
            "ON",
            "    dep_acct_realtime_indicator.i_dep_acct_no_offline_00001 = cust_realtime_indicator.target_id",
        ]

    @staticmethod
    def _uses_cust_realtime_indicator(alias_mapping: Optional[Dict[str, str]]) -> bool:
        """判断规则是否引用了客户实时指标（别名映射 values 含 cust_realtime_indicator）。"""
        return bool(alias_mapping) and 'cust_realtime_indicator' in alias_mapping.values()

    def _get_latest_version_snapshot(
        self,
        db: Session,
        wide_table_name: str,
        etl_date: date
    ) -> VersionSelectionResult:
        """获取指定日期的最新版本快照

        策略：
        1. 查找该宽表在该日期的所有 ready 状态的快照
        2. 按版本创建时间降序排序，取最新版本
        3. 如果没有快照，返回空结果

        Args:
            db: 数据库会话
            wide_table_name: 宽表名称
            etl_date: ETL日期

        Returns:
            VersionSelectionResult: 版本选择结果
        """
        # 查找该日期所有 ready 状态的快照（both 双写下同版本可能有 postgresql/duckdb 两条）
        ready_snapshots = db.query(FraudHunterWideTableSnapshot).join(
            FraudHunterWideTableVersion,
            FraudHunterWideTableSnapshot.version_hash == FraudHunterWideTableVersion.version_hash
        ).filter(
            and_(
                FraudHunterWideTableSnapshot.wide_table_name == wide_table_name,
                FraudHunterWideTableSnapshot.etl_date == etl_date,
                FraudHunterWideTableSnapshot.status == 'ready'
            )
        ).order_by(
            desc(FraudHunterWideTableVersion.created_at)
        ).all()

        if not ready_snapshots:
            return VersionSelectionResult(
                version_hash='',
                wide_table_name=wide_table_name,
                etl_date=etl_date,
                parquet_path=None,
                message=f"未找到 {wide_table_name} 在 {etl_date} 的可用快照"
            )

        # 按配置的存储后端优先选择快照（duckdb/both 优先 duckdb，否则 postgresql）
        preferred_backend = (
            'duckdb'
            if settings.fraudhunter_wide_table_offline_store in ('duckdb', 'both')
            else 'postgresql'
        )
        latest_snapshot = next(
            (
                s for s in ready_snapshots
                if (getattr(s, 'storage_backend', None) or 'postgresql') == preferred_backend
            ),
            ready_snapshots[0]
        )

        # 使用最新版本
        version_hash = latest_snapshot.version_hash or ''
        storage_backend = getattr(latest_snapshot, 'storage_backend', None) or 'postgresql'

        logger.info(
            f"选择最新版本: {wide_table_name}, 日期={etl_date}, "
            f"版本={version_hash[:8]}..., backend={storage_backend}, "
            f"创建时间={latest_snapshot.generation_time}"
        )

        return VersionSelectionResult(
            version_hash=version_hash,
            wide_table_name=latest_snapshot.wide_table_name,
            etl_date=latest_snapshot.etl_date,
            parquet_path=latest_snapshot.parquet_file_path,
            message=f"使用版本 {version_hash[:8]}",
            storage_backend=storage_backend
        )

    @staticmethod
    def _extract_indicator_codes_from_model(model: FraudHunterModelDefinition) -> List[str]:
        """从模型定义中提取使用的指标编码列表"""
        indicator_codes_json = model.indicator_codes
        if not indicator_codes_json:
            return []

        if isinstance(indicator_codes_json, str):
            try:
                return json.loads(indicator_codes_json)
            except (json.JSONDecodeError, TypeError):
                return []
        elif isinstance(indicator_codes_json, list):
            return indicator_codes_json
        return []

    def _generate_backtest_sql(
        self,
        db: Session,
        model: FraudHunterModelDefinition,
        dep_acct_realtime_table_name: str,
        dep_acct_offline_table_name: str,
        cust_offline_table_name: str,
        etl_date: date,
        cust_realtime_table_name: Optional[str] = None,
        dialect: str = 'postgresql',
    ) -> str:
        """生成历史回测SQL

        SQL结构：
        - 实时指标使用当天的存款宽表（dep_acct_no_realtime_indicator）
        - 离线指标使用前一天的存款宽表（dep_acct_no_offline_indicator）
        - 客户离线指标使用前一天的客户宽表（cust_offline_indicator）
        - 客户实时指标使用当天的客户宽表（cust_realtime_indicator，可选）

        Args:
            db: 数据库会话
            model: 模型定义
            dep_acct_realtime_table_name: 实时（当天）存款宽表引用（PG表名或duckdb引用）
            dep_acct_offline_table_name: 离线（前一天）存款宽表引用
            cust_offline_table_name: 离线（前一天）客户宽表引用
            etl_date: 执行日期
            cust_realtime_table_name: 当天客户宽表引用（可选）
            dialect: SQL方言（postgresql=PG执行；duckdb=DuckDB执行）

        Returns:
            回测SQL语句
        """
        rule_config_dict = model.rule_config

        # 将 Dict 转换为 RuleConfig 模型
        rule_config = RuleConfig(**rule_config_dict)

        # 使用 RuleEngine 构建指标别名映射并生成 WHERE 子句
        rule_engine = RuleEngine(db=db)  # 传入数据库会话以获取指标中文名
        indicator_alias_mapping = rule_engine.build_indicator_alias_mapping(
            rule_config,
            use_alias=True
        )

        # 生成SELECT子句
        select_fields = [f'dep_acct_realtime_indicator.target_id as "账号"']
        select_fields.append(f'dep_acct_realtime_indicator.etl_date as "实时数据日期"')

        # 根据别名映射添加字段，使用中文别名（实时指标带[实时]前缀）
        if indicator_alias_mapping:
            for indicator, alias in indicator_alias_mapping.items():
                if indicator in ('__T0__', '__T_1__'):
                    continue
                # 获取指标的中文显示名称（实时指标带[实时]前缀）
                display_name = rule_engine._get_indicator_display_name(indicator)
                select_fields.append(f'{alias}.{indicator} AS "{display_name}"')

        select_clause = ",\n    ".join(select_fields)

        # 生成WHERE子句，使用 RuleEngine（方言随执行引擎）
        where_clause = rule_engine.generate_sql_expression(
            rule_config,
            indicator_alias_mapping,
            numeric_columns_are_typed=True,
            dialect=dialect
        )

        # 构建 FROM/JOIN 子句（含可选的客户实时 JOIN）
        from_join_lines = [
            "FROM",
            f"    {dep_acct_realtime_table_name} as dep_acct_realtime_indicator",
            "LEFT JOIN",
            f"    {dep_acct_offline_table_name} as dep_acct_offline_indicator",
            "ON",
            "    dep_acct_realtime_indicator.target_id = dep_acct_offline_indicator.target_id",
            "LEFT JOIN",
            f"    {cust_offline_table_name} as cust_offline_indicator",
            "ON",
            "    dep_acct_realtime_indicator.i_dep_acct_no_offline_00001 = cust_offline_indicator.target_id",
        ]
        from_join_lines.extend(self._build_cust_realtime_join_clause(cust_realtime_table_name))
        from_join_clause = "\n".join(from_join_lines)

        # 生成完整SQL - 使用PG表
        sql = f"""-- 模型历史回测SQL
-- 模型: {model.model_code} ({model.model_name})
-- 执行日期: {etl_date.strftime('%Y-%m-%d')}

SELECT
    {select_clause}
{from_join_clause}
WHERE
    {where_clause}
LIMIT 10000
"""
        return sql

    async def execute_backtest(
        self,
        db: Session,
        execution_id: str,
        model_id: int,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """执行模型历史回测

        Args:
            db: 数据库会话
            execution_id: 执行ID
            model_id: 模型ID
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)

        Returns:
            执行结果摘要
        """
        # 获取模型定义
        model = db.query(FraudHunterModelDefinition).filter(
            FraudHunterModelDefinition.id == model_id
        ).first()

        if not model:
            raise ValueError(f"模型不存在: {model_id}")

        # 获取执行记录
        execution = db.query(FraudHunterDryRunExecution).filter(
            FraudHunterDryRunExecution.execution_id == execution_id
        ).first()

        if not execution:
            raise ValueError(f"执行记录不存在: {execution_id}")

        # 解析日期
        start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()

        # 获取宽表名称（目前只支持dep_acct_no）
        dep_acct_wide_table_name = self.get_wide_table_name('dep_acct_no')
        cust_wide_table_name = self.get_wide_table_name('cust_no')

        logger.info(f"开始执行模型历史回测: {model.model_code}, 日期范围: {start_date} 至 {end_date}")

        # 更新执行记录参数
        execution.parameters = {
            'model_id': model_id,
            'model_code': model.model_code,
            'start_date': start_date,
            'end_date': end_date,
            'wide_table_name': dep_acct_wide_table_name
        }
        db.flush()

        # 执行结果
        results = {
            'total_days': 0,
            'success_days': 0,
            'skipped_days': 0,
            'failed_days': 0,
            'daily_results': [],
            'warnings': [],
            'generated_sqls': [],
            'matched_records': [],  # 存储所有命中记录
            'version_fallbacks': []  # 存储版本降级信息
        }

        # 提取模型使用的指标编码
        model_indicator_codes = self._extract_indicator_codes_from_model(model)
        logger.info(f"模型使用的指标: {model_indicator_codes}")

        # 获取白名单账户列表
        whitelist_acct = SystemConfigManager(db).get_config_value('whitelist_acct', default=[])
        whitelist_set = set(whitelist_acct) if whitelist_acct else set()
        if whitelist_set:
            logger.info(f"加载白名单账户 {len(whitelist_set)} 个")

        # 获取模型级别的白名单账户列表
        model_whitelist_acct_raw = SystemConfigManager(db).get_config_value('model_whitelist_acct', default=[])
        model_whitelist_acct = build_model_whitelist_dict(model_whitelist_acct_raw)
        if model_whitelist_acct:
            logger.info(f"加载模型白名单配置，模型数={len(model_whitelist_acct)}")

        # 按日执行
        current_date = start_dt
        while current_date <= end_dt:
            results['total_days'] += 1
            previous_date = current_date - timedelta(days=1)

            day_result = {
                'date': current_date.strftime('%Y-%m-%d'),
                'status': 'pending',
                'message': '',
                'rows_matched': 0,
                'version_fallbacks': {}
            }

            try:
                # 获取当天的最新版本快照（实时指标）
                dep_acct_realtime_result = self._get_latest_version_snapshot(
                    db, dep_acct_wide_table_name, current_date
                )

                # 获取前一天的最新版本快照（离线指标）
                dep_acct_offline_result = self._get_latest_version_snapshot(
                    db, dep_acct_wide_table_name, previous_date
                )
                cust_offline_result = self._get_latest_version_snapshot(
                    db, cust_wide_table_name, previous_date
                )

                # 获取当天的最新版本客户宽表快照（用于客户实时指标，与 dep_acct_realtime 同口径）
                cust_realtime_result = self._get_latest_version_snapshot(
                    db, cust_wide_table_name, current_date
                )

                # 记录版本信息
                day_result['version_fallbacks'] = {
                    'realtime': dep_acct_realtime_result.version_hash[:8] if dep_acct_realtime_result.version_hash else '',
                    'offline': dep_acct_offline_result.version_hash[:8] if dep_acct_offline_result.version_hash else '',
                    'cust': cust_offline_result.version_hash[:8] if cust_offline_result.version_hash else ''
                }
                results['version_fallbacks'].append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    **day_result['version_fallbacks']
                })

                dep_acct_realtime_table = dep_acct_realtime_result.pg_table_name
                dep_acct_offline_table = dep_acct_offline_result.pg_table_name
                cust_offline_table = cust_offline_result.pg_table_name
                cust_realtime_table = cust_realtime_result.pg_table_name

                # 按快照存储后端路由：任一离线快照为 duckdb → DuckDB 执行，
                # PG 侧表（实时表/PG离线表）经 ATTACH 别名 pg_rt 引用
                duckdb_mode = query_router.requires_duckdb(
                    dep_acct_offline_result, cust_offline_result
                )
                sql_dialect = 'duckdb' if duckdb_mode else 'postgresql'

                if not dep_acct_realtime_table:
                    warning_msg = f"日期 {current_date} 的宽表不存在，跳过"
                    logger.warning(warning_msg)
                    results['warnings'].append(warning_msg)
                    results['skipped_days'] += 1
                    day_result['status'] = 'skipped'
                    day_result['message'] = '当天宽表不存在'
                    results['daily_results'].append(day_result)
                    current_date += timedelta(days=1)
                    continue

                if not dep_acct_offline_table or not cust_offline_table:
                    warning_msg = f"日期 {previous_date} 的宽表不存在（用于离线指标），跳过 {current_date}"
                    logger.warning(warning_msg)
                    results['warnings'].append(warning_msg)
                    results['skipped_days'] += 1
                    day_result['status'] = 'skipped'
                    day_result['message'] = '前一天宽表不存在'
                    results['daily_results'].append(day_result)
                    current_date += timedelta(days=1)
                    continue

                # 判断模型是否引用客户实时指标；引用且当天客户宽表缺失则跳过当天
                rule_config_for_check = RuleConfig(**model.rule_config)
                check_engine = RuleEngine(db=db)
                alias_mapping_for_check = check_engine.build_indicator_alias_mapping(
                    rule_config_for_check, use_alias=True
                )
                uses_cust_realtime = self._uses_cust_realtime_indicator(alias_mapping_for_check)
                if uses_cust_realtime and not cust_realtime_table:
                    warning_msg = f"日期 {current_date} 的当天客户宽表不存在，无法回测客户实时指标，跳过"
                    logger.warning(warning_msg)
                    results['warnings'].append(warning_msg)
                    results['skipped_days'] += 1
                    day_result['status'] = 'skipped'
                    day_result['message'] = '当天客户宽表不存在（客户实时指标）'
                    results['daily_results'].append(day_result)
                    current_date += timedelta(days=1)
                    continue

                # 表引用转换（duckdb 模式：duckdb 快照 → read_parquet，PG 侧表 → pg_rt 前缀）
                dep_acct_realtime_ref = query_router.offline_table_ref(
                    dep_acct_realtime_result, current_date, duckdb_mode
                )
                dep_acct_offline_ref = query_router.offline_table_ref(
                    dep_acct_offline_result, previous_date, duckdb_mode
                )
                cust_offline_ref = query_router.offline_table_ref(
                    cust_offline_result, previous_date, duckdb_mode
                )
                cust_realtime_ref = (
                    query_router.offline_table_ref(
                        cust_realtime_result, current_date, duckdb_mode
                    )
                    if uses_cust_realtime else None
                )

                # 生成SQL（仅当模型引用客户实时指标时才传入当天客户宽表，避免无谓 JOIN）
                sql = self._generate_backtest_sql(
                    db,
                    model,
                    dep_acct_realtime_ref,
                    dep_acct_offline_ref,
                    cust_offline_ref,
                    current_date,
                    cust_realtime_ref,
                    dialect=sql_dialect,
                )

                logger.info(f"模型sql已生成：{sql[:200]} ..................................... {sql[-200:]}")

                results['generated_sqls'].append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    'sql': sql
                })

                # 执行SQL（按快照后端选择执行引擎）
                if duckdb_mode:
                    with get_query_session(attach_pg=True) as duck_session:
                        execute_result_df = duck_session.execute_df(sql)
                else:
                    execute_result_df = AnalyzeDBConnector.execute_sql(sql, fetch_df=True)
                execute_result = execute_result_df if execute_result_df is not None else None

                day_result['status'] = 'success'
                day_result['message'] = '执行成功'
                day_result['rows_matched'] = len(execute_result) if execute_result is not None else 0
                results['success_days'] += 1

                # 收集命中记录到结果集
                if execute_result is not None and len(execute_result) > 0:
                    records = execute_result.to_dict('records')
                    
                    records = [
                        {
                            k: None if (
                                v is None 
                                or (isinstance(v, float) and (math.isnan(v) or math.isinf(v)))
                            ) else v
                            for k, v in r.items()
                        }
                        for r in records
                    ]

                    # 为每条记录添加白名单标记并过滤模型白名单
                    filtered_records = []
                    for record in records:
                        account_id = str(record.get('账号', ''))

                        # 检查全局白名单
                        is_global_whitelist = account_id in whitelist_set
                        record['是否白名单'] = is_global_whitelist

                        # 添加模型ID和模型名称字段
                        record['模型编码'] = model.model_code
                        record['模型名称'] = model.model_name

                        # 检查模型白名单（如果账号在模型白名单中，则跳过该记录）
                        model_whitelist = model_whitelist_acct.get(model.id, [])
                        if model_whitelist and account_id in model_whitelist:
                            logger.debug(
                                f"跳过模型白名单账户: 账号={account_id}, "
                                f"模型={model.model_code}"
                            )
                            continue

                        filtered_records.append(record)

                    results['matched_records'].extend(filtered_records)

                logger.info(f"日期 {current_date} 回测完成，命中 {day_result['rows_matched']} 条记录")

            except Exception as e:
                error_msg = f"日期 {current_date} 回测失败: {str(e)}"
                logger.error(error_msg, exc_info=True)
                logger.exception(error_msg)
                results['failed_days'] += 1
                day_result['status'] = 'failed'
                day_result['message'] = str(e)

            results['daily_results'].append(day_result)
            current_date += timedelta(days=1)

            # 模拟间隔
            await asyncio.sleep(0.5)

        # 更新执行记录
        execution.rows_processed = results['total_days']
        execution.rows_output = results['success_days']

        total_matched = sum(r.get('rows_matched', 0) for r in results['daily_results'])
        results['total_rows_matched'] = total_matched

        log_content = f"""[模型历史回测执行日志]
模型: {model.model_code} ({model.model_name})
执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
日期范围: {start_date} 至 {end_date}

执行结果:
- 总天数: {results['total_days']}
- 成功天数: {results['success_days']}
- 跳过天数: {results['skipped_days']}
- 失败天数: {results['failed_days']}
- 总命中记录数: {total_matched}

每日执行详情:
{self._format_daily_results(results['daily_results'])}

警告信息:
{chr(10).join(results['warnings']) if results['warnings'] else '无'}
"""
        execution.log_content = log_content
        results['log_content'] = log_content  # 将日志内容也加入返回结果

        # 将版本信息和完整结果保存到 result_summary
        execution.result_summary = {
            'total_days': results['total_days'],
            'success_days': results['success_days'],
            'skipped_days': results['skipped_days'],
            'failed_days': results['failed_days'],
            'total_rows_matched': total_matched,
            'version_fallbacks': results['version_fallbacks'],
            'warnings': results['warnings']
        }

        db.commit()

        logger.info(f"模型历史回测完成: {model.model_code}, 成功 {results['success_days']}/{results['total_days']} 天")

        return results

    async def execute_batch_backtest(
        self,
        db: Session,
        execution_id: str,
        task_id: int,
        model_ids: List[int],
        start_date: str,
        end_date: str,
        submitted_by: str,
        max_concurrency: int = 3
    ) -> Dict[str, Any]:
        """执行模型批量历史回测父任务。

        父任务只保存固定维度的聚合结果；每个模型的动态指标明细保留在子回测任务中。
        """
        from services.fraudhunter.dry_run_task_service import dry_run_task_manager

        execution = db.query(FraudHunterDryRunExecution).filter(
            FraudHunterDryRunExecution.execution_id == execution_id
        ).first()
        if not execution:
            raise ValueError(f"批量执行记录不存在: {execution_id}")

        unique_model_ids = list(dict.fromkeys(model_ids))
        models = db.query(FraudHunterModelDefinition).filter(
            FraudHunterModelDefinition.id.in_(unique_model_ids)
        ).all()
        model_by_id = {model.id: model for model in models}
        ordered_models = [model_by_id[model_id] for model_id in unique_model_ids if model_id in model_by_id]

        execution.parameters = {
            'model_ids': unique_model_ids,
            'start_date': start_date,
            'end_date': end_date,
            'max_concurrency': max_concurrency
        }
        db.flush()

        child_execution_ids: List[str] = []
        logger.info(
            f"开始执行模型批量历史回测: execution_id={execution_id}, "
            f"模型数={len(ordered_models)}, 日期范围={start_date} 至 {end_date}"
        )

        max_concurrency = max(1, max_concurrency)
        for start_index in range(0, len(ordered_models), max_concurrency):
            batch_models = ordered_models[start_index:start_index + max_concurrency]
            running_child_tasks = []

            for model in batch_models:
                child_execution_id = await dry_run_task_manager.submit_task(
                    db=db,
                    task_type='model_backtest',
                    task_id=model.id,
                    task_func=self.execute_backtest,
                    created_by=submitted_by,
                    task_name=model.model_name,
                    parent_execution_id=execution_id,
                    start_date=start_date,
                    end_date=end_date
                )
                child_execution_ids.append(child_execution_id)
                child_task = dry_run_task_manager.running_tasks.get(child_execution_id)
                if child_task:
                    running_child_tasks.append(child_task)

            if running_child_tasks:
                await asyncio.gather(*running_child_tasks, return_exceptions=True)

        db.expire_all()
        child_executions = db.query(FraudHunterDryRunExecution).filter(
            FraudHunterDryRunExecution.parent_execution_id == execution_id
        ).all()

        child_by_model_id = {child.task_id: child for child in child_executions}
        account_hit_map: Dict[str, Dict[str, Any]] = {}
        daily_summary_map: Dict[str, Dict[str, Any]] = {}
        model_summaries: List[Dict[str, Any]] = []
        failed_models_detail: List[Dict[str, Any]] = []
        warnings: List[str] = []
        total_hit_records = 0

        for model in ordered_models:
            child = child_by_model_id.get(model.id)
            if not child:
                failed_models_detail.append({
                    'model_id': model.id,
                    'model_code': model.model_code,
                    'model_name': model.model_name,
                    'status': 'failed',
                    'message': '未找到子任务执行记录'
                })
                continue

            result = child.result_summary or {}
            matched_records = result.get('matched_records') or []
            daily_results = result.get('daily_results') or []
            model_hit_accounts = set()
            model_hit_records = len(matched_records)
            total_hit_records += model_hit_records

            for warning in result.get('warnings') or []:
                warnings.append(f"{model.model_code}: {warning}")

            for day in daily_results:
                date_value = day.get('date', '')
                if not date_value:
                    continue
                day_summary = daily_summary_map.setdefault(date_value, {
                    'date': date_value,
                    'success_models': 0,
                    'failed_models': 0,
                    'skipped_models': 0,
                    'hit_records': 0,
                    'hit_accounts': set()
                })
                status = day.get('status')
                if status == 'success':
                    day_summary['success_models'] += 1
                elif status == 'failed':
                    day_summary['failed_models'] += 1
                elif status == 'skipped':
                    day_summary['skipped_models'] += 1
                day_summary['hit_records'] += day.get('rows_matched', 0) or 0

            for record in matched_records:
                account = str(record.get('账号', '') or '').strip()
                if not account:
                    continue

                model_hit_accounts.add(account)
                hit_date = str(record.get('实时数据日期', '') or '').strip()
                is_whitelist = bool(record.get('是否白名单', False))

                account_summary = account_hit_map.setdefault(account, {
                    'account': account,
                    'hit_model_count': 0,
                    'hit_models': [],
                    'hit_dates': set(),
                    'is_whitelist': is_whitelist
                })

                if is_whitelist:
                    account_summary['is_whitelist'] = True

                if hit_date:
                    account_summary['hit_dates'].add(hit_date)
                    day_summary = daily_summary_map.setdefault(hit_date, {
                        'date': hit_date,
                        'success_models': 0,
                        'failed_models': 0,
                        'skipped_models': 0,
                        'hit_records': 0,
                        'hit_accounts': set()
                    })
                    day_summary['hit_accounts'].add(account)

                if not any(hit_model['model_id'] == model.id for hit_model in account_summary['hit_models']):
                    account_summary['hit_models'].append({
                        'model_id': model.id,
                        'model_code': model.model_code,
                        'model_name': model.model_name,
                        'child_task_id': child.id,
                        'child_execution_id': child.execution_id
                    })

            success_days = result.get('success_days', 0)
            failed_days = result.get('failed_days', 0)
            skipped_days = result.get('skipped_days', 0)

            model_summary = {
                'model_id': model.id,
                'model_code': model.model_code,
                'model_name': model.model_name,
                'status': child.status,
                'child_task_id': child.id,
                'child_execution_id': child.execution_id,
                'total_rows_matched': result.get('total_rows_matched', model_hit_records),
                'hit_accounts': len(model_hit_accounts),
                'total_days': result.get('total_days', 0),
                'success_days': success_days,
                'failed_days': failed_days,
                'skipped_days': skipped_days,
                'error_message': child.error_message
            }
            model_summaries.append(model_summary)

            if child.status == 'failed':
                failed_models_detail.append({
                    'model_id': model.id,
                    'model_code': model.model_code,
                    'model_name': model.model_name,
                    'status': child.status,
                    'message': child.error_message or result.get('error') or '子任务执行失败',
                    'child_task_id': child.id,
                    'child_execution_id': child.execution_id
                })

        account_hit_summaries = []
        for account_summary in account_hit_map.values():
            hit_models = account_summary['hit_models']
            account_hit_summaries.append({
                'account': account_summary['account'],
                'hit_model_count': len(hit_models),
                'hit_models': hit_models,
                'hit_dates': sorted(account_summary['hit_dates']),
                'is_whitelist': account_summary['is_whitelist']
            })

        account_hit_summaries.sort(
            key=lambda item: (item['hit_model_count'], len(item['hit_dates'])),
            reverse=True
        )

        daily_summaries = []
        for day_summary in daily_summary_map.values():
            daily_summaries.append({
                'date': day_summary['date'],
                'success_models': day_summary['success_models'],
                'failed_models': day_summary['failed_models'],
                'skipped_models': day_summary['skipped_models'],
                'hit_records': day_summary['hit_records'],
                'hit_accounts': len(day_summary['hit_accounts'])
            })
        daily_summaries.sort(key=lambda item: item['date'])

        success_models = sum(1 for item in model_summaries if item['status'] == 'success')
        failed_models = sum(1 for item in model_summaries if item['status'] == 'failed')
        cancelled_models = sum(1 for item in model_summaries if item['status'] == 'cancelled')

        summary = {
            'task_type': 'model_batch_backtest',
            'start_date': start_date,
            'end_date': end_date,
            'model_count': len(ordered_models),
            'success_models': success_models,
            'failed_models': failed_models,
            'cancelled_models': cancelled_models,
            'total_hit_accounts': len(account_hit_summaries),
            'total_hit_records': total_hit_records,
            'child_execution_ids': child_execution_ids,
            'model_summaries': model_summaries,
            'account_hit_summaries': account_hit_summaries,
            'daily_summaries': daily_summaries,
            'warnings': warnings,
            'failed_models_detail': failed_models_detail,
            'log_content': self._format_batch_log(
                execution_id=execution_id,
                start_date=start_date,
                end_date=end_date,
                model_summaries=model_summaries,
                total_hit_accounts=len(account_hit_summaries),
                total_hit_records=total_hit_records,
                warnings=warnings
            )
        }

        execution.rows_processed = len(ordered_models)
        execution.rows_output = success_models
        execution.log_content = summary['log_content']
        db.commit()

        logger.info(
            f"模型批量历史回测完成: execution_id={execution_id}, "
            f"成功模型={success_models}/{len(ordered_models)}, "
            f"命中账号={len(account_hit_summaries)}"
        )

        return summary

    def _format_batch_log(
        self,
        execution_id: str,
        start_date: str,
        end_date: str,
        model_summaries: List[Dict[str, Any]],
        total_hit_accounts: int,
        total_hit_records: int,
        warnings: List[str]
    ) -> str:
        """格式化批量回测日志。"""
        lines = [
            "[模型批量历史回测执行日志]",
            f"执行ID: {execution_id}",
            f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"日期范围: {start_date} 至 {end_date}",
            "",
            "执行结果:",
            f"- 模型数量: {len(model_summaries)}",
            f"- 成功模型: {sum(1 for item in model_summaries if item['status'] == 'success')}",
            f"- 失败模型: {sum(1 for item in model_summaries if item['status'] == 'failed')}",
            f"- 命中账号数: {total_hit_accounts}",
            f"- 命中记录数: {total_hit_records}",
            "",
            "模型执行详情:"
        ]
        for item in model_summaries:
            lines.append(
                f"  - {item['model_code']} {item['model_name']}: "
                f"{item['status']}, 命中账号={item['hit_accounts']}, "
                f"命中记录={item['total_rows_matched']}"
            )

        lines.extend([
            "",
            "警告信息:",
            "\n".join(warnings) if warnings else "无"
        ])
        return "\n".join(lines)

    def _format_daily_results(self, daily_results: List[Dict[str, Any]]) -> str:
        """格式化每日执行结果为日志文本

        Args:
            daily_results: 每日执行结果列表

        Returns:
            格式化的文本
        """
        lines = []
        for dr in daily_results:
            status_emoji = {
                'success': '✓',
                'skipped': '⊘',
                'failed': '✗',
                'pending': '○'
            }.get(dr['status'], '?')
            base_info = f"  {status_emoji} {dr['date']}: {dr['message']} (命中: {dr['rows_matched']})"

            # 如果有版本信息，追加显示
            if dr.get('version_fallbacks'):
                ver = dr['version_fallbacks']
                base_info += f" [实时:{ver.get('realtime', '')} 离线:{ver.get('offline', '')} 客户:{ver.get('cust', '')}]"

            lines.append(base_info)
        return chr(10).join(lines) if lines else '无'


# 全局模型执行器实例
model_executor = ModelExecutor()
