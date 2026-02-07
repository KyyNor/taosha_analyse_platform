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

    @property
    def pg_table_name(self) -> Optional[str]:
        """获取PG表名"""
        if not self.version_hash:
            return None
        return f"{self.wide_table_name}_{self.version_hash}_{self.etl_date.strftime('%Y%m%d')}"


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
        # 查找该日期所有 ready 状态的快照
        latest_snapshot = db.query(FraudHunterWideTableSnapshot).join(
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
        ).first()

        if not latest_snapshot:
            return VersionSelectionResult(
                version_hash='',
                wide_table_name=wide_table_name,
                etl_date=etl_date,
                parquet_path=None,
                message=f"未找到 {wide_table_name} 在 {etl_date} 的可用快照"
            )

        # 使用最新版本
        version_hash = latest_snapshot.version_hash or ''

        logger.info(
            f"选择最新版本: {wide_table_name}, 日期={etl_date}, "
            f"版本={version_hash[:8]}..., 创建时间={latest_snapshot.generation_time}"
        )

        return VersionSelectionResult(
            version_hash=version_hash,
            wide_table_name=latest_snapshot.wide_table_name,
            etl_date=latest_snapshot.etl_date,
            parquet_path=latest_snapshot.parquet_file_path,
            message=f"使用版本 {version_hash[:8]}"
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
        etl_date: date
    ) -> str:
        """生成历史回测SQL

        SQL结构：
        - 实时指标使用当天的存款宽表（dep_acct_no_realtime_indicator）
        - 离线指标使用前一天的存款宽表（dep_acct_no_offline_indicator）
        - 客户离线指标使用前一天的客户宽表（cust_offline_indicator）

        Args:
            db: 数据库会话
            model: 模型定义
            dep_acct_realtime_table_name: 实时（当天）存款宽表PG表名
            dep_acct_offline_table_name: 离线（前一天）存款宽表PG表名
            cust_offline_table_name: 离线（前一天）客户宽表PG表名
            etl_date: 执行日期

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

        # 生成WHERE子句，使用 RuleEngine
        where_clause = rule_engine.generate_sql_expression(rule_config, indicator_alias_mapping)

        # 生成完整SQL - 使用PG表
        sql = f"""-- 模型历史回测SQL
-- 模型: {model.model_code} ({model.model_name})
-- 执行日期: {etl_date.strftime('%Y-%m-%d')}

SELECT
    {select_clause}
FROM
    {dep_acct_realtime_table_name} as dep_acct_realtime_indicator
LEFT JOIN
    {dep_acct_offline_table_name} as dep_acct_offline_indicator
ON
    dep_acct_realtime_indicator.target_id = dep_acct_offline_indicator.target_id
LEFT JOIN
    {cust_offline_table_name} as cust_offline_indicator
ON
    dep_acct_realtime_indicator.i_dep_acct_no_offline_00001 = cust_offline_indicator.target_id
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
        # 配置格式: [{'模型编号':'55', '白名单账号':'124124'}, {'模型编号':'32', '白名单账号':'22323'}]
        # 转换为: {"model_code_1": ["acct1", "acct2"], "model_code_2": ["acct3"]}
        model_whitelist_acct_raw = SystemConfigManager(db).get_config_value('model_whitelist_acct', default=[])
        model_whitelist_acct = {}
        if model_whitelist_acct_raw:
            for item in model_whitelist_acct_raw:
                model_code = item.get('模型编号', '')
                account_id = item.get('白名单账号', '')
                if model_code and account_id:
                    if model_code not in model_whitelist_acct:
                        model_whitelist_acct[model_code] = []
                    model_whitelist_acct[model_code].append(account_id)
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

                # 生成SQL
                sql = self._generate_backtest_sql(
                    db,
                    model,
                    dep_acct_realtime_table,
                    dep_acct_offline_table,
                    cust_offline_table,
                    current_date
                )

                logger.info(f"模型sql已生成：{sql[:200]} ..................................... {sql[-200:]}")

                results['generated_sqls'].append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    'sql': sql
                })

                # 执行SQL（使用PG执行）
                execute_result_df = AnalyzeDBConnector.execute_sql(sql, fetch_df=True)
                execute_result = execute_result_df if execute_result_df is not None else None

                day_result['status'] = 'success'
                day_result['message'] = '执行成功'
                day_result['rows_matched'] = len(execute_result) if execute_result is not None else 0
                results['success_days'] += 1

                # 收集命中记录到结果集
                if execute_result is not None and len(execute_result) > 0:
                    records = execute_result.to_dict('records')
                    # 为每条记录添加白名单标记并过滤模型白名单
                    filtered_records = []
                    for record in records:
                        account_id = str(record.get('账号', ''))

                        # 检查全局白名单
                        is_global_whitelist = account_id in whitelist_set
                        record['是否白名单'] = is_global_whitelist

                        # 检查模型白名单（如果账号在模型白名单中，则跳过该记录）
                        model_whitelist = model_whitelist_acct.get(model.model_code, [])
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
