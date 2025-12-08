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

    def _extract_indicators_from_rule_config(self, rule_config: Dict) -> Dict[str, str]:
        """从规则配置中提取指标及其时效性
        
        根据指标编码判断时效性：
        - 包含 'realtime' 的为实时指标
        - 包含 'offline' 的为离线指标
        - 默认为离线指标
        
        Args:
            rule_config: 规则配置字典
            
        Returns:
            指标字典 {indicator_code: 'realtime' | 'offline'}
        """
        indicators = {}

        def extract_from_rule(rule: Dict):
            if rule.get('type') == 'condition':
                indicator = rule.get('indicator', '')
                if indicator:
                    # 根据指标编码判断时效性
                    if 'realtime' in indicator.lower():
                        indicators[indicator] = 'realtime'
                    else:
                        indicators[indicator] = 'offline'
            elif rule.get('type') == 'group':
                for sub_rule in rule.get('rules', []):
                    extract_from_rule(sub_rule)

        for rule in rule_config.get('rules', []):
            extract_from_rule(rule)

        return indicators

    def _generate_backtest_sql(
        self,
        model: FraudHunterModelDefinition,
        realtime_parquet_path: str,
        offline_parquet_path: str,
        etl_date: date
    ) -> str:
        """生成历史回测SQL
        
        SQL结构：
        - 实时指标使用当天的宽表（realtime_dep_acct_no_indicator）
        - 离线指标使用前一天的宽表（offline_dep_acct_no_indicator）
        
        Args:
            model: 模型定义
            realtime_parquet_path: 实时（当天）宽表parquet路径
            offline_parquet_path: 离线（前一天）宽表parquet路径
            etl_date: 执行日期
            
        Returns:
            回测SQL语句
        """
        rule_config = model.rule_config
        
        # 提取指标及其时效性
        indicators = self._extract_indicators_from_rule_config(rule_config)
        
        # 生成SELECT子句
        select_fields = [f"realtime_indicator.target_id"]
        select_fields.append(f"etl_date")
        
        for indicator, timeliness in indicators.items():
            if timeliness == 'realtime':
                select_fields.append(f"realtime_indicator.{indicator} as realtime_{indicator}")
            else:
                select_fields.append(f"offline_indicator.{indicator} as offline_{indicator}")
        
        select_clause = ",\n    ".join(select_fields)
        
        # 生成WHERE子句，替换表别名
        where_clause = self._generate_where_clause_with_alias(rule_config, indicators)
        
        # 获取输出配置
        output = rule_config.get('output', {})
        
        # 生成完整SQL
        sql = f"""-- 模型历史回测SQL
-- 模型: {model.model_code} ({model.model_name})
-- 执行日期: {etl_date.strftime('%Y-%m-%d')}

SELECT
    {select_clause}
FROM
    read_parquet('{realtime_parquet_path}') as realtime_indicator
LEFT JOIN
    read_parquet('{offline_parquet_path}') as offline_indicator
ON
    realtime_indicator.target_id = offline_indicator.target_id
WHERE
    {where_clause}
"""
        return sql

    def _generate_where_clause_with_alias(
        self,
        rule_config: Dict,
        indicators: Dict[str, str]
    ) -> str:
        """生成带表别名的WHERE子句
        
        根据指标的时效性，使用对应的表别名
        
        Args:
            rule_config: 规则配置
            indicators: 指标时效性映射
            
        Returns:
            WHERE子句
        """
        def condition_to_sql(condition: Dict) -> str:
            """将条件转换为SQL"""
            indicator = condition.get('indicator', '')
            operator = condition.get('operator', '=')
            value = condition.get('value', {})
            
            # 确定表别名
            timeliness = indicators.get(indicator, 'offline')
            table_alias = 'realtime_indicator' if timeliness == 'realtime' else 'offline_indicator'
            qualified_indicator = f"{table_alias}.{indicator}"
            
            # 处理值
            if isinstance(value, dict):
                # 值表达式
                value_type = value.get('type', 'constant')
                if value_type == 'constant':
                    actual_value = value.get('value')
                elif value_type == 'indicator':
                    ref_indicator = value.get('indicator', '')
                    ref_timeliness = indicators.get(ref_indicator, 'offline')
                    ref_alias = 'realtime_indicator' if ref_timeliness == 'realtime' else 'offline_indicator'
                    actual_value = f"{ref_alias}.{ref_indicator}"
                    return f"{qualified_indicator} {operator} {actual_value}"
                else:
                    actual_value = value.get('value')
            else:
                actual_value = value
            
            # 格式化值
            if operator in ['in', 'not in']:
                if isinstance(actual_value, list):
                    formatted_values = ', '.join([
                        f"'{v}'" if isinstance(v, str) else str(v)
                        for v in actual_value
                    ])
                    op_sql = 'IN' if operator == 'in' else 'NOT IN'
                    return f"{qualified_indicator} {op_sql} ({formatted_values})"
            elif operator in ['regexp', 'not regexp']:
                pattern = actual_value if isinstance(actual_value, str) else '|'.join(actual_value)
                op_sql = 'REGEXP' if operator == 'regexp' else 'NOT REGEXP'
                return f"{qualified_indicator} {op_sql} '{pattern}'"
            else:
                # 基础比较操作符
                if isinstance(actual_value, str):
                    return f"{qualified_indicator} {operator} '{actual_value}'"
                elif isinstance(actual_value, bool):
                    return f"{qualified_indicator} {operator} {'TRUE' if actual_value else 'FALSE'}"
                else:
                    return f"{qualified_indicator} {operator} {actual_value}"
            
            return "1=1"

        def group_to_sql(group: Dict) -> str:
            """将规则组转换为SQL"""
            rules = group.get('rules', [])
            logic = group.get('logic', 'AND')
            
            if not rules:
                return "1=1"
            
            sub_expressions = []
            for rule in rules:
                if rule.get('type') == 'condition':
                    sub_expressions.append(condition_to_sql(rule))
                elif rule.get('type') == 'group':
                    sub_expressions.append(f"({group_to_sql(rule)})")
            
            logic_op = ' AND ' if logic == 'AND' else ' OR '
            return logic_op.join(sub_expressions)

        # 构建根表达式
        root_group = {
            'type': 'group',
            'logic': rule_config.get('logic', 'AND'),
            'rules': rule_config.get('rules', [])
        }
        
        return f"({group_to_sql(root_group)})"

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
        wide_table_name = self._get_wide_table_name(model.object_type)

        logger.info(f"开始执行模型历史回测: {model.model_code}, 日期范围: {start_date} 至 {end_date}")

        # 更新执行记录参数
        execution.parameters = {
            'model_id': model_id,
            'model_code': model.model_code,
            'start_date': start_date,
            'end_date': end_date,
            'wide_table_name': wide_table_name
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
            'generated_sqls': []
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
                realtime_parquet = self._get_parquet_path(db, wide_table_name, current_date)
                
                # 获取前一天的parquet路径（离线指标）
                offline_parquet = self._get_parquet_path(db, wide_table_name, previous_date)

                if not realtime_parquet:
                    warning_msg = f"日期 {current_date} 的宽表文件不存在，跳过"
                    logger.warning(warning_msg)
                    results['warnings'].append(warning_msg)
                    results['skipped_days'] += 1
                    day_result['status'] = 'skipped'
                    day_result['message'] = '当天宽表文件不存在'
                    results['daily_results'].append(day_result)
                    current_date += timedelta(days=1)
                    continue

                if not offline_parquet:
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
                    realtime_parquet,
                    offline_parquet,
                    current_date
                )

                results['generated_sqls'].append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    'sql': sql
                })

                # 模拟SQL执行（实际应该调用Spark/DuckDB执行）
                with duckdb.connect(":memory:") as duckdb_con:
                    execute_result = duckdb_con.execute(sql).df()

                day_result['status'] = 'success'
                day_result['message'] = '执行成功'
                day_result['rows_matched'] = len(execute_result)
                results['success_days'] += 1

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

        log_content = f"""
[模型历史回测执行日志]
模型: {model.model_code} ({model.model_name})
执行时间: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}
日期范围: {start_date} 至 {end_date}

执行结果:
- 总天数: {results['total_days']}
- 成功天数: {results['success_days']}
- 跳过天数: {results['skipped_days']}
- 失败天数: {results['failed_days']}
- 总命中记录数: {total_matched}

警告信息:
{chr(10).join(results['warnings']) if results['warnings'] else '无'}
"""
        execution.log_content = log_content
        db.commit()

        logger.info(f"模型历史回测完成: {model.model_code}, 成功 {results['success_days']}/{results['total_days']} 天")

        return results


# 全局模型执行器实例
model_executor = ModelExecutor()