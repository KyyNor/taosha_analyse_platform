"""
模型历史回测执行器

负责执行模型的历史回测任务，生成SQL并按日执行
"""

import asyncio
import json
import duckdb
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_

from models.fraudhunter.risk_control_model import FraudHunterModelDefinition
from models.fraudhunter.wide_table import (
    FraudHunterWideTableVersion,
    FraudHunterWideTableSnapshot
)
from models.fraudhunter.dry_run_task import FraudHunterDryRunExecution
from schemas.fraudhunter.rule import RuleConfig, ConditionRule, GroupRule, Rule
from services.fraudhunter.model_service.rule_engine import RuleEngine
from utils.logger import logger


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
        """获取指定日期的宽表parquet文件路径
        
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

    def _generate_backtest_sql(
        self,
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
        - 离线指标使用前一天的存款宽表（dep_acct_no_offline_indicator）
        
        Args:
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
        rule_engine = RuleEngine(db=None)  # 不需要数据库会话
        indicator_alias_mapping = rule_engine.build_indicator_alias_mapping(
            rule_config,
            use_alias=True
        )
        
        # 生成SELECT子句
        select_fields = [f"dep_acct_realtime_indicator.target_id"]
        select_fields.append(f"etl_date")
        
        # 根据别名映射添加字段
        if indicator_alias_mapping:
            for indicator, alias in indicator_alias_mapping.items():
                select_fields.append(f"{alias}.{indicator}")
        
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
            'matched_records': []  # 新增：存储所有命中记录
        }

        # 按日执行
        current_date = start_dt
        while current_date <= end_dt:
            results['total_days'] += 1
            previous_date = current_date - timedelta(days=1)

            day_result = {
                'date': current_date.strftime('%Y-%m-%d'),
                'status': 'pending',
                'message': '',
                'rows_matched': 0
            }

            try:
                # 获取当天的parquet路径（实时指标）
                dep_acct_realtime_parquet = self._get_parquet_path(db, dep_acct_wide_table_name, current_date)
                
                # 获取前一天的parquet路径（离线指标）
                dep_acct_offline_parquet = self._get_parquet_path(db, dep_acct_wide_table_name, previous_date)
                cust_offline_parquet = self._get_parquet_path(db, cust_wide_table_name, previous_date)

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
                    model,
                    dep_acct_realtime_parquet,
                    dep_acct_offline_parquet,
                    cust_offline_parquet,
                    current_date
                )

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
执行时间: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}
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
            lines.append(f"  {status_emoji} {dr['date']}: {dr['message']} (命中: {dr['rows_matched']})")
        return chr(10).join(lines) if lines else '无'


# 全局模型执行器实例
model_executor = ModelExecutor()