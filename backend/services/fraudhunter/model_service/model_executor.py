"""
模型历史回测执行器

负责执行模型的历史回测任务，生成SQL并按日执行

支持主备版本智能降级:
- 优先使用current版本宽表
- 当指标版本不匹配时自动降级到target版本
- 记录降级日志供排查
"""

import asyncio
import json
import duckdb
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_

from models.db_base import get_db_session
from models.fraudhunter.risk_control_model import FraudHunterModelDefinition
from models.fraudhunter.indicator import FraudHunterIndicatorDefinition
from models.fraudhunter.wide_table import (
    FraudHunterWideTableVersion,
    FraudHunterWideTableSnapshot
)
from models.fraudhunter.dry_run_task import FraudHunterDryRunExecution
from schemas.fraudhunter.rule import RuleConfig, ConditionRule, GroupRule, Rule
from services.fraudhunter.model_service.rule_engine import RuleEngine
from utils.logger import logger


@dataclass
class VersionSelectionResult:
    """版本选择结果"""
    version_hash: str                           # 选中的版本hash
    parquet_path: Optional[str]                 # 文件路径
    is_fallback: bool = False                   # 是否降级
    fallback_reason: Optional[str] = None       # 降级原因类型
    mismatched_indicators: List[Dict] = field(default_factory=list)  # 不匹配指标详情
    message: str = ""                           # 用户友好的提示信息
    
    def get_fallback_summary(self) -> str:
        """获取降级摘要信息"""
        if not self.is_fallback:
            return ""
        
        lines = [f"[版本降级] 使用target版本宽表，原因: {self.fallback_reason}"]
        for ind in self.mismatched_indicators:
            lines.append(f"  - {ind.get('indicator_code')}: {ind.get('message')}")
        return "\n".join(lines)


class ModelExecutor:
    """模型执行器 - 历史回测专用"""

    # 对象类型到宽表名称的映射
    OBJECT_TYPE_TO_WIDE_TABLE = {
        'dep_acct_no': 'dep_acct_wide_table',
        'cust_no': 'cust_wide_table',
        'loan_acct_no': 'loan_acct_wide_table'
    }

    def __init__(self):
        pass

    def _get_wide_table_name(self, object_type: str) -> str:
        """获取宽表名称
        
        Args:
            object_type: 对象类型
            
        Returns:
            宽表名称
        """
        return self.OBJECT_TYPE_TO_WIDE_TABLE.get(object_type, 'dep_acct_wide_table')

    def _get_parquet_path(
        self,
        db: Session,
        wide_table_name: str,
        etl_date: date
    ) -> Optional[str]:
        """获取指定日期的宽表parquet文件路径（简单版本，无降级）
        
        从 fraudhunter_wide_table_version 中 status = current 的 version_hash
        关联 fraudhunter_wide_table_snapshot 获取 parquet_file_path
        
        Args:
            db: 数据库会话
            wide_table_name: 宽表名称
            etl_date: ETL日期
            
        Returns:
            parquet文件路径，如果不存在返回None
        """
        # 获取当前版本的version_hash
        current_version = db.query(FraudHunterWideTableVersion).filter(
            and_(
                FraudHunterWideTableVersion.wide_table_name == wide_table_name,
                FraudHunterWideTableVersion.status == 'current'
            )
        ).first()

        if not current_version:
            logger.warning(f"未找到 {wide_table_name} 的当前版本")
            return None

        # 获取对应日期的快照
        snapshot = db.query(FraudHunterWideTableSnapshot).filter(
            and_(
                FraudHunterWideTableSnapshot.version_hash == current_version.version_hash,
                FraudHunterWideTableSnapshot.etl_date == etl_date,
                FraudHunterWideTableSnapshot.status == 'ready'
            )
        ).first()

        if not snapshot:
            logger.warning(f"未找到 {wide_table_name} 在 {etl_date} 的快照")
            return None

        return snapshot.parquet_file_path

    def _get_parquet_path_with_fallback(
        self,
        db: Session,
        wide_table_name: str,
        etl_date: date,
        model_indicator_codes: List[str]
    ) -> VersionSelectionResult:
        """获取指定日期的宽表parquet文件路径（支持智能降级）
        
        降级逻辑：
        1. 如果current版本不存在 → 使用target版本
        2. 如果模型使用的指标仅在target版本存在 → 使用target版本
        3. 如果指标的current_version > 宽表记录的版本号 → 使用target版本
        
        Args:
            db: 数据库会话
            wide_table_name: 宽表名称
            etl_date: ETL日期
            model_indicator_codes: 模型使用的指标编码列表
            
        Returns:
            VersionSelectionResult: 版本选择结果
        """
        # 1. 获取current和target版本
        current_version = self._get_version_by_status(db, wide_table_name, 'current')
        target_version = self._get_version_by_status(db, wide_table_name, 'target')
        
        # 2. 如果没有current版本，直接使用target
        if not current_version:
            if target_version:
                return self._build_selection_result(
                    db, target_version, etl_date,
                    is_fallback=True,
                    fallback_reason='current_not_exist',
                    message=f"{wide_table_name} 没有current版本，使用target版本"
                )
            else:
                return VersionSelectionResult(
                    version_hash='',
                    parquet_path=None,
                    message=f"{wide_table_name} 没有可用的版本"
                )
        
        # 3. 检查指标版本匹配
        mismatched_indicators = self._check_indicators_version_match(
            db, current_version, model_indicator_codes
        )
        
        # 4. 如果存在不匹配，尝试使用target版本
        if mismatched_indicators:
            if target_version:
                # 尝试从target获取
                target_result = self._build_selection_result(
                    db, target_version, etl_date,
                    is_fallback=True,
                    fallback_reason=mismatched_indicators[0].get('reason', 'indicator_mismatch'),
                    mismatched_indicators=mismatched_indicators,
                    message=self._build_fallback_message(mismatched_indicators)
                )
                # 如果target版本有数据，使用target
                if target_result.parquet_path:
                    return target_result
            
            # target也没有数据，尝试用current（可能部分指标缺失）
            logger.warning(
                f"指标版本不匹配但target版本也无数据，尝试使用current版本: "
                f"{[i['indicator_code'] for i in mismatched_indicators]}"
            )
        
        # 5. 使用current版本
        return self._build_selection_result(
            db, current_version, etl_date,
            is_fallback=False
        )

    def _get_version_by_status(
        self,
        db: Session,
        wide_table_name: str,
        status: str
    ) -> Optional[FraudHunterWideTableVersion]:
        """根据状态获取宽表版本"""
        return db.query(FraudHunterWideTableVersion).filter(
            and_(
                FraudHunterWideTableVersion.wide_table_name == wide_table_name,
                FraudHunterWideTableVersion.status == status
            )
        ).first()

    def _build_selection_result(
        self,
        db: Session,
        version: FraudHunterWideTableVersion,
        etl_date: date,
        is_fallback: bool = False,
        fallback_reason: Optional[str] = None,
        mismatched_indicators: List[Dict] = None,
        message: str = ""
    ) -> VersionSelectionResult:
        """构建版本选择结果"""
        # 获取快照
        snapshot = db.query(FraudHunterWideTableSnapshot).filter(
            and_(
                FraudHunterWideTableSnapshot.version_hash == version.version_hash,
                FraudHunterWideTableSnapshot.etl_date == etl_date,
                FraudHunterWideTableSnapshot.status == 'ready'
            )
        ).first()
        
        return VersionSelectionResult(
            version_hash=version.version_hash,
            parquet_path=snapshot.parquet_file_path if snapshot else None,
            is_fallback=is_fallback,
            fallback_reason=fallback_reason,
            mismatched_indicators=mismatched_indicators or [],
            message=message
        )

    def _check_indicators_version_match(
        self,
        db: Session,
        current_version: FraudHunterWideTableVersion,
        indicator_codes: List[str]
    ) -> List[Dict]:
        """检查指标版本是否与宽表版本匹配
        
        Args:
            db: 数据库会话
            current_version: 当前版本对象
            indicator_codes: 模型使用的指标编码列表
            
        Returns:
            不匹配的指标列表
        """
        mismatched = []
        metadata = current_version.indicator_metadata or {}
        
        # 构建indicator_code到metadata的映射
        code_to_meta = {}
        for ind_id, ind_meta in metadata.items():
            code = ind_meta.get('indicator_code')
            if code:
                code_to_meta[code] = ind_meta
        
        for indicator_code in indicator_codes:
            # 查询当前指标定义
            indicator = db.query(FraudHunterIndicatorDefinition).filter(
                FraudHunterIndicatorDefinition.indicator_code == indicator_code
            ).first()
            
            if not indicator:
                # 指标不存在，可能是配置错误，跳过
                continue
            
            # 只检查离线指标
            if indicator.indicator_type != 'offline':
                continue
            
            # 检查是否在current版本的metadata中
            indicator_in_version = code_to_meta.get(indicator_code)
            
            # 情况1：指标不在current版本中（新上线的指标）
            if not indicator_in_version:
                mismatched.append({
                    'indicator_code': indicator_code,
                    'indicator_name': indicator.indicator_name,
                    'reason': 'indicator_not_in_current',
                    'message': f'指标 [{indicator.indicator_name}] 仅在target版本存在（新上线指标）'
                })
                continue
            
            # 情况2：指标版本已升级
            version_in_wide_table = indicator_in_version.get('version', 0)
            if indicator.current_version > version_in_wide_table:
                mismatched.append({
                    'indicator_code': indicator_code,
                    'indicator_name': indicator.indicator_name,
                    'reason': 'indicator_version_upgraded',
                    'message': f'指标 [{indicator.indicator_name}] 已升级: v{version_in_wide_table} → v{indicator.current_version}',
                    'old_version': version_in_wide_table,
                    'new_version': indicator.current_version
                })
        
        return mismatched

    def _build_fallback_message(self, mismatched_indicators: List[Dict]) -> str:
        """构建降级提示信息"""
        if not mismatched_indicators:
            return ""
        
        reasons = []
        for ind in mismatched_indicators:
            reasons.append(f"- {ind.get('message', ind.get('indicator_code'))}")
        
        return "因以下指标变动切换到target版本:\n" + "\n".join(reasons)

    def _collect_fallback_info(
        self,
        wide_table_name: str,
        etl_date: date,
        selection_result: VersionSelectionResult,
        expected_version: str,
        fallback_logs: List[Dict]
    ):
        """收集版本降级信息到列表（供后续汇总到result_summary）
        
        Args:
            wide_table_name: 宽表名称
            etl_date: ETL日期
            selection_result: 版本选择结果
            expected_version: 期望的版本（current）
            fallback_logs: 降级日志列表（用于收集）
        """
        if not selection_result.is_fallback:
            return
        
        fallback_logs.append({
            'wide_table_name': wide_table_name,
            'etl_date': str(etl_date),
            'expected_version': expected_version[:8] if expected_version else '',
            'actual_version': selection_result.version_hash[:8] if selection_result.version_hash else '',
            'fallback_reason': selection_result.fallback_reason or 'unknown',
            'mismatched_indicators': selection_result.mismatched_indicators,
            'message': selection_result.message
        })
        
        logger.info(
            f"[版本降级] 宽表={wide_table_name}, 日期={etl_date}, "
            f"原因={selection_result.fallback_reason}, "
            f"影响指标={[i['indicator_code'] for i in selection_result.mismatched_indicators]}"
        )

    def _extract_indicator_codes_from_model(self, model: FraudHunterModelDefinition) -> List[str]:
        """从模型定义中提取使用的指标编码列表
        
        Args:
            model: 模型定义
            
        Returns:
            指标编码列表
        """
        indicator_codes_json = model.indicator_codes
        if not indicator_codes_json:
            return []
        
        try:
            if isinstance(indicator_codes_json, str):
                return json.loads(indicator_codes_json)
            elif isinstance(indicator_codes_json, list):
                return indicator_codes_json
            return []
        except (json.JSONDecodeError, TypeError):
            return []

    def _generate_backtest_sql(
        self,
        db: Session,
        model: FraudHunterModelDefinition,
        dep_acct_realtime_parquet_path: str,
        dep_acct_offline_parquet_path: str,
        cust_offline_parquet_path: str,
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
            dep_acct_realtime_parquet_path: 实时（当天）存款宽表parquet路径
            dep_acct_offline_parquet_path: 离线（前一天）存款宽表parquet路径
            cust_offline_parquet_path: 离线（前一天）客户宽表parquet路径
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
                # 获取指标的中文显示名称（实时指标带[实时]前缀）
                display_name = rule_engine._get_indicator_display_name(indicator)
                select_fields.append(f'{alias}.{indicator} AS "{display_name}"')
        
        select_clause = ",\n    ".join(select_fields)
        
        # 生成WHERE子句，使用 RuleEngine
        where_clause = rule_engine.generate_sql_expression(rule_config, indicator_alias_mapping)
        
        # 生成完整SQL
        sql = f"""-- 模型历史回测SQL
-- 模型: {model.model_code} ({model.model_name})
-- 执行日期: {etl_date.strftime('%Y-%m-%d')}

SELECT
    {select_clause}
FROM
    read_parquet('{dep_acct_realtime_parquet_path}') as dep_acct_realtime_indicator
LEFT JOIN
    read_parquet('{dep_acct_offline_parquet_path}') as dep_acct_offline_indicator
ON
    dep_acct_realtime_indicator.target_id = dep_acct_offline_indicator.target_id
LEFT JOIN 
    read_parquet('{cust_offline_parquet_path}') as cust_offline_indicator
ON
    dep_acct_realtime_indicator.i_dep_acct_no_offline_00001 = cust_offline_indicator.target_id
WHERE
    {where_clause}
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
        dep_acct_wide_table_name = self._get_wide_table_name('dep_acct_no')
        cust_wide_table_name = self._get_wide_table_name('cust_no')

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
        
        # 获取current版本信息（用于降级日志记录）
        current_dep_version = self._get_version_by_status(db, dep_acct_wide_table_name, 'current')
        current_cust_version = self._get_version_by_status(db, cust_wide_table_name, 'current')
        
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
                'version_fallback': None  # 新增：记录降级信息
            }

            try:
                # 获取当天的parquet路径（实时指标）- 使用智能降级
                dep_acct_realtime_result = self._get_parquet_path_with_fallback(
                    db, dep_acct_wide_table_name, current_date, model_indicator_codes
                )
                
                # 获取前一天的parquet路径（离线指标）- 使用智能降级
                dep_acct_offline_result = self._get_parquet_path_with_fallback(
                    db, dep_acct_wide_table_name, previous_date, model_indicator_codes
                )
                cust_offline_result = self._get_parquet_path_with_fallback(
                    db, cust_wide_table_name, previous_date, model_indicator_codes
                )
                
                # 收集降级信息
                if dep_acct_realtime_result.is_fallback:
                    self._collect_fallback_info(
                        dep_acct_wide_table_name, current_date, dep_acct_realtime_result,
                        current_dep_version.version_hash if current_dep_version else '',
                        results['version_fallbacks']
                    )
                    day_result['version_fallback'] = dep_acct_realtime_result.get_fallback_summary()
                
                if dep_acct_offline_result.is_fallback:
                    self._collect_fallback_info(
                        dep_acct_wide_table_name, previous_date, dep_acct_offline_result,
                        current_dep_version.version_hash if current_dep_version else '',
                        results['version_fallbacks']
                    )
                
                if cust_offline_result.is_fallback:
                    self._collect_fallback_info(
                        cust_wide_table_name, previous_date, cust_offline_result,
                        current_cust_version.version_hash if current_cust_version else '',
                        results['version_fallbacks']
                    )
                
                dep_acct_realtime_parquet = dep_acct_realtime_result.parquet_path
                dep_acct_offline_parquet = dep_acct_offline_result.parquet_path
                cust_offline_parquet = cust_offline_result.parquet_path

                if not dep_acct_realtime_parquet:
                    warning_msg = f"日期 {current_date} 的宽表文件不存在，跳过"
                    logger.warning(warning_msg)
                    results['warnings'].append(warning_msg)
                    results['skipped_days'] += 1
                    day_result['status'] = 'skipped'
                    day_result['message'] = '当天宽表文件不存在'
                    results['daily_results'].append(day_result)
                    current_date += timedelta(days=1)
                    continue

                if not dep_acct_offline_parquet or not cust_offline_parquet:
                    warning_msg = f"日期 {previous_date} 的宽表文件不存在（用于离线指标），跳过 {current_date}"
                    logger.warning(warning_msg)
                    results['warnings'].append(warning_msg)
                    results['skipped_days'] += 1
                    day_result['status'] = 'skipped'
                    day_result['message'] = '前一天宽表文件不存在'
                    results['daily_results'].append(day_result)
                    current_date += timedelta(days=1)
                    continue

                # 生成SQL
                sql = self._generate_backtest_sql(
                    db,
                    model,
                    dep_acct_realtime_parquet,
                    dep_acct_offline_parquet,
                    cust_offline_parquet,
                    current_date
                )
                
                logger.info(f"模型sql已生成：{sql[:200]} ..................................... {sql[-200:]}")

                results['generated_sqls'].append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    'sql': sql
                })

                # 执行SQL（使用DuckDB执行）
                with duckdb.connect(":memory:") as duckdb_con:
                    execute_result = duckdb_con.execute(sql).df()

                day_result['status'] = 'success'
                day_result['message'] = '执行成功'
                day_result['rows_matched'] = len(execute_result)
                results['success_days'] += 1

                # 收集命中记录到结果集
                if len(execute_result) > 0:
                    records = execute_result.to_dict('records')
                    results['matched_records'].extend(records)

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
        
        # 将降级信息和完整结果保存到 result_summary
        execution.result_summary = {
            'total_days': results['total_days'],
            'success_days': results['success_days'],
            'skipped_days': results['skipped_days'],
            'failed_days': results['failed_days'],
            'total_rows_matched': total_matched,
            'version_fallbacks': results['version_fallbacks'],  # 降级信息
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
            
            # 如果有降级信息，追加显示
            if dr.get('version_fallback'):
                base_info += f"\n      ⚠️ {dr['version_fallback']}"
            
            lines.append(base_info)
        return chr(10).join(lines) if lines else '无'


# 全局模型执行器实例
model_executor = ModelExecutor()