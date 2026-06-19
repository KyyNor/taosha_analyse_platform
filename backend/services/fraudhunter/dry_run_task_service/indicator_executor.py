"""
指标执行器（Spark SQL执行 - 支持真实Spark连接）
修复MySQL连接超时问题
"""

import asyncio
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta, timezone
import pandas as pd
from sqlalchemy.orm import Session
from models.fraudhunter.indicator import FraudHunterIndicatorTask, FraudHunterIndicatorDefinition
from models.fraudhunter.dry_run_task import FraudHunterDryRunExecution
from schemas.fraudhunter.indicator import IndicatorTaskCreate
from services.fraudhunter.wide_table_service.numeric_type_utils import WideTableNumericTypeHelper
from utils.logger import logger
from utils.spark_utils import spark_utils
from models.db_base import SessionLocal


class IndicatorExecutor:
    """指标执行器

    修复MySQL连接超时问题
    """

    def _replace_date_variables(self, sql: str, etl_date: Optional[str] = None) -> str:
        """替换SQL中的日期变量

        Args:
            sql: SQL语句
            etl_date: ETL日期，格式YYYY-MM-DD，如果为None则使用昨天

        Returns:
            替换后的SQL语句
        """

        # todo 需要页面配置
        if etl_date is None:
            # 默认使用昨天
            etl_date = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')

        # 替换 ${date} 变量
        replaced_sql = sql.replace('${date}', etl_date)

        logger.info(f"日期变量替换: {etl_date}")
        return replaced_sql, etl_date

    def _validate_output_fields(self, sample_result: List[Dict[str, Any]], indicator_ids: List[int], db: Session) -> Dict[str, Any]:
        """验证输出字段是否符合要求

        Args:
            sample_result: 样本结果数据
            indicator_ids: 关联的指标ID列表
            db: 数据库会话

        Returns:
            验证结果
        """
        if not sample_result:
            return {
                'valid': False,
                'error': '没有返回数据',
                'missing_fields': [],
                'extra_fields': []
            }

        # 获取所有关联指标的编码
        indicators = db.query(FraudHunterIndicatorDefinition).filter(
            FraudHunterIndicatorDefinition.id.in_(indicator_ids)
        ).all()

        indicator_codes = [ind.indicator_code for ind in indicators]

        # 获取返回数据的字段
        output_fields = set(sample_result[0].keys()) if sample_result else set()

        # 必须包含的字段
        required_fields = {'target_id', 'etl_date'}
        required_fields.update(indicator_codes)

        # 检查缺失的字段
        missing_fields = required_fields - output_fields

        # 检查多余的字段（可选警告）
        extra_fields = output_fields - required_fields

        is_valid = len(missing_fields) == 0

        validation_result = {
            'valid': is_valid,
            'required_fields': list(required_fields),
            'actual_fields': list(output_fields),
            'missing_fields': list(missing_fields),
            'extra_fields': list(extra_fields),
            'indicator_codes': indicator_codes
        }

        if is_valid:
            logger.info(f"字段验证通过: 必需字段 {required_fields} 都存在")
        else:
            logger.warning(f"字段验证失败: 缺失字段 {missing_fields}")

        return validation_result

    async def execute_dry_run(
        self,
        db: Session,
        execution_id: str,
        task_id: int,
        etl_date: str,
        sample_size: int = 100,
        task_version: int = None,
        validate_fields: bool = False,
        indicator_ids: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """执行指标任务试运行（模拟）

        Args:
            db: 数据库会话
            execution_id: 执行ID
            task_id: 指标任务ID
            etl_date: ETL日期
            sample_size: 样本大小
            task_version: 指标任务版本号（可选）
            validate_fields: 是否验证输出字段
            indicator_ids: 关联的指标ID列表（字段验证时使用）

        Returns:
            执行结果摘要
        """
        # 获取指标任务
        task = db.query(FraudHunterIndicatorTask).filter(
            FraudHunterIndicatorTask.id == task_id
        ).first()

        if not task:
            raise ValueError(f"指标任务不存在: {task_id}")

        # 确定使用的版本
        version = task_version if task_version else task.current_version

        logger.info(f"开始执行指标任务试运行: {task.task_code}, 版本: {version}, ETL日期: {etl_date}")

        # 获取干运行执行记录
        execution = db.query(FraudHunterDryRunExecution).filter(
            FraudHunterDryRunExecution.execution_id == execution_id
        ).first()

        if not execution:
            raise ValueError(f"执行记录不存在: {execution_id}")
        
        # 替换SQL中的日期变量
        processed_sql, etl_date = self._replace_date_variables(task.logic_content, etl_date)
        
        # 更新执行详情
        execution.etl_date = datetime.strptime(etl_date, '%Y-%m-%d').date()
        execution.version = version
        execution.parameters = {
            'task_id': task_id,
            'task_code': task.task_code,
            'etl_date': etl_date,
            'sample_size': sample_size
        }
        db.flush()

        try:
            # 获取关联的指标编码（用于生成模拟数据和字段验证）
            indicator_codes = None
            if validate_fields and indicator_ids:
                indicators = db.query(FraudHunterIndicatorDefinition).filter(
                    FraudHunterIndicatorDefinition.id.in_(indicator_ids)
                ).all()
                indicator_codes = [ind.indicator_code for ind in indicators]

            # 调用Spark JDBC连接执行
            result = await self._spark_execution(
                processed_sql,
                etl_date,
                sample_size,
                indicator_codes
            )

            numeric_conversion_stats = []
            if indicator_ids:
                indicators = db.query(FraudHunterIndicatorDefinition).filter(
                    FraudHunterIndicatorDefinition.id.in_(indicator_ids)
                ).all()
                stats_metadata = {
                    str(ind.id): {
                        'indicator_code': ind.indicator_code,
                        'data_type': ind.data_type,
                    }
                    for ind in indicators
                }
                _, conversion_stats = WideTableNumericTypeHelper.convert_numeric_dataframe_columns(
                    pd.DataFrame(result['sample_result']),
                    stats_metadata,
                )
                numeric_conversion_stats = [stat.__dict__ for stat in conversion_stats]

            # 字段验证（如果启用）
            validation_result = None
            if validate_fields and indicator_ids:
                # 重新获取数据库会话以避免连接超时
                validation_result = self._validate_output_fields_with_fresh_db(
                    result['sample_result'], indicator_ids
                )

                # 如果验证失败，记录错误但仍然返回结果
                if not validation_result['valid']:
                    logger.warning(f"任务 {task.task_code} 字段验证失败")

            # 更新执行记录
            execution.rows_processed = result['rows_processed']
            execution.rows_output = result['rows_output']
            execution.duration_seconds = result['duration_seconds']
            execution.log_content = result['log_content']

            db.commit()

            logger.info(f"指标任务试运行完成: {task.task_code}, 处理 {result['rows_processed']} 行")

            return {
                'total_records': result['rows_output'],
                'sample_result': result['sample_result'],
                'execution_time_seconds': result['duration_seconds'],
                'validation_result': validation_result,
                'numeric_conversion_stats': numeric_conversion_stats,
                'processed_sql': processed_sql
            }

        except Exception as e:
            # 记录错误
            execution.error_message = str(e)
            db.commit()

            logger.error(f"指标任务试运行失败: {task.task_code}, 错误: {str(e)}")
            raise

    def _validate_output_fields_with_fresh_db(self, sample_result: List[Dict[str, Any]], indicator_ids: List[int]) -> Dict[str, Any]:
        """使用新的数据库会话来验证输出字段（避免连接超时）

        Args:
            sample_result: 样本结果数据
            indicator_ids: 关联的指标ID列表

        Returns:
            验证结果
        """
        # 创建新的数据库会话
        fresh_db = SessionLocal()
        try:
            return self._validate_output_fields(sample_result, indicator_ids, fresh_db)
        finally:
            fresh_db.close()

    async def _spark_execution(
        self,
        sql: str,
        etl_date: str,
        sample_size: int,
        indicator_codes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """执行Spark SQL查询（真实连接）

        Args:
            sql: SQL语句
            etl_date: ETL日期
            sample_size: 样本大小（用于LIMIT限制返回记录数）
            indicator_codes: 指标编码列表（可选，不影响实际执行）

        Returns:
            执行结果
        """
        start_time = datetime.now(timezone.utc)
        logger.info(f"开始执行Spark SQL查询，ETL日期: {etl_date}，样本大小: {sample_size}")

        try:
            # 添加LIMIT子句限制返回记录数
            # 如果SQL中已经包含LIMIT，则不重复添加
            if 'limit' not in sql.lower():
                # 简单处理：在SQL末尾添加LIMIT（更复杂的情况可能需要SQL解析）
                limited_sql = f"{sql.rstrip(';')} LIMIT {sample_size}"
            else:
                limited_sql = sql
                logger.warning(f"SQL中已包含LIMIT子句，将不再添加样本大小限制")

            logger.debug(f"执行的SQL语句: {limited_sql}")

            # 使用异步执行避免阻塞事件循环
            loop = asyncio.get_event_loop()
            sample_result = await loop.run_in_executor(
                None,
                spark_utils.query_sql,
                limited_sql
            )

            # 计算执行时间
            end_time = datetime.now(timezone.utc)
            duration_seconds = (end_time - start_time).total_seconds()

            # 统计实际返回的记录数
            rows_output = len(sample_result)

            # 生成执行日志
            log_content = f"""
[Spark执行日志]
执行时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}
完成时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}
执行耗时: {duration_seconds:.2f} 秒
ETL日期: {etl_date}
样本大小: {sample_size}

执行的SQL语句:
{limited_sql}

执行结果:
- 输出记录数: {rows_output}
- 执行状态: 成功
"""

            logger.info(f"Spark SQL查询完成，返回 {rows_output} 条记录，耗时 {duration_seconds:.2f} 秒")

            return {
                'rows_processed': rows_output,  # 实际处理的行数
                'rows_output': rows_output,      # 输出的行数
                'duration_seconds': duration_seconds,
                'sample_result': sample_result,  # list[dict] 格式
                'log_content': log_content
            }

        except Exception as e:
            # 计算执行时间（即使失败）
            end_time = datetime.now(timezone.utc)
            duration_seconds = (end_time - start_time).total_seconds()

            # 记录错误日志
            error_message = str(e)
            logger.error(f"Spark SQL查询执行失败: {error_message}")

            log_content = f"""
[Spark执行日志 - 失败]
执行时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}
失败时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}
执行耗时: {duration_seconds:.2f} 秒
ETL日期: {etl_date}
样本大小: {sample_size}

执行的SQL语句:
{sql}

错误信息:
{error_message}

执行状态: 失败
"""

            # 重新抛出异常，让上层处理
            raise RuntimeError(f"Spark SQL执行失败: {error_message}") from e

    async def validate_task_logic(
            self,
            db: Session,
            task_data: IndicatorTaskCreate,
            indicator_ids: List[int],
            etl_date: Optional[str] = None,
            sample_size: int = 10
        ) -> Dict[str, Any]:
            """验证任务逻辑（不需要创建任务）

            在创建任务前验证SQL逻辑和字段输出
            修复MySQL连接超时问题

            Args:
                db: 数据库会话
                task_data: 任务数据
                indicator_ids: 关联的指标ID列表
                etl_date: ETL日期，如果为None则使用昨天
                sample_size: 样本大小

            Returns:
                验证结果
            """
            logger.info(f"开始验证任务逻辑，关联 {len(indicator_ids)} 个指标")

            # 替换SQL中的日期变量
            processed_sql, etl_date = self._replace_date_variables(task_data.logic_content, etl_date)

            # 先获取需要的指标编码（避免长时间操作后连接失效）
            indicator_codes = self._get_indicator_codes_with_fresh_db(indicator_ids)

            # 执行Spark SQL（可能耗时较长）
            result = await self._spark_execution(
                processed_sql,
                etl_date,
                sample_size,
                indicator_codes
            )

            # 字段验证（使用新的数据库会话）
            validation_result = self._validate_output_fields_with_fresh_db(
                result['sample_result'], indicator_ids
            )

            return {
                'sql_valid': True,
                'execution_success': True,
                'field_validation': validation_result,
                'sample_result': result['sample_result'],
                'processed_sql': processed_sql,
                'execution_time_seconds': result['duration_seconds'],
                'etl_date_used': etl_date,
                'indicator_codes': indicator_codes
            }

    def _get_indicator_codes_with_fresh_db(self, indicator_ids: List[int]) -> List[str]:
        """使用新的数据库会话获取指标编码

        Args:
            indicator_ids: 指标ID列表

        Returns:
            指标编码列表
        """
        fresh_db = SessionLocal()
        try:
            indicators = fresh_db.query(FraudHunterIndicatorDefinition).filter(
                FraudHunterIndicatorDefinition.id.in_(indicator_ids)
            ).all()

            if len(indicators) != len(indicator_ids):
                found_ids = [ind.id for ind in indicators]
                missing_ids = set(indicator_ids) - set(found_ids)
                raise ValueError(f"指标不存在: {missing_ids}")

            return [ind.indicator_code for ind in indicators]
        finally:
            fresh_db.close()


# 全局指标执行器实例
indicator_executor = IndicatorExecutor()
