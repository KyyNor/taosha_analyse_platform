"""
指标执行器（模拟Spark SQL执行）
"""

import asyncio
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from models.fraudhunter.indicator import FraudHunterIndicatorTask, FraudHunterIndicatorDefinition
from models.fraudhunter.task import FraudHunterTaskExecutionRecord
from schemas.fraudhunter.indicator import IndicatorTaskCreate
from utils.logger import logger


class IndicatorExecutor:
    """指标执行器

    由于实际Spark环境尚未集成，此处提供模拟执行功能
    支持变量替换和字段验证
    """

    def _replace_date_variables(self, sql: str, etl_date: Optional[str] = None) -> str:
        """替换SQL中的日期变量

        Args:
            sql: SQL语句
            etl_date: ETL日期，格式YYYY-MM-DD，如果为None则使用昨天

        Returns:
            替换后的SQL语句
        """
        if etl_date is None:
            # 默认使用昨天
            etl_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

        # 替换 ${date} 变量
        replaced_sql = sql.replace('${date}', etl_date)

        logger.info(f"日期变量替换: {etl_date}")
        return replaced_sql

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

        # 记录执行详情
        record = FraudHunterTaskExecutionRecord(
            execution_id=execution_id,
            etl_date=datetime.strptime(etl_date, '%Y-%m-%d').date(),
            version=version,
            parameters={
                'task_id': task_id,
                'task_code': task.task_code,
                'etl_date': etl_date,
                'sample_size': sample_size
            }
        )
        db.add(record)
        db.flush()

        try:
            # 替换SQL中的日期变量
            processed_sql = self._replace_date_variables(task.logic_content, etl_date)

            # 获取关联的指标编码（用于生成模拟数据和字段验证）
            indicator_codes = None
            if validate_fields and indicator_ids:
                indicators = db.query(FraudHunterIndicatorDefinition).filter(
                    FraudHunterIndicatorDefinition.id.in_(indicator_ids)
                ).all()
                indicator_codes = [ind.indicator_code for ind in indicators]

            # 模拟SQL执行（实际应该调用Spark JDBC连接执行）
            result = await self._mock_spark_execution(
                processed_sql,
                etl_date,
                sample_size,
                indicator_codes
            )

            # 字段验证（如果启用）
            validation_result = None
            if validate_fields and indicator_ids:
                validation_result = self._validate_output_fields(
                    result['sample_result'], indicator_ids, db
                )

                # 如果验证失败，记录错误但仍然返回结果
                if not validation_result['valid']:
                    logger.warning(f"任务 {task.task_code} 字段验证失败")

            # 更新记录
            record.rows_processed = result['rows_processed']
            record.rows_output = result['rows_output']
            record.duration_seconds = result['duration_seconds']
            record.log_content = result['log_content']

            db.commit()

            logger.info(f"指标任务试运行完成: {task.task_code}, 处理 {result['rows_processed']} 行")

            return {
                'total_records': result['rows_output'],
                'sample_result': result['sample_result'],
                'execution_time_seconds': result['duration_seconds'],
                'validation_result': validation_result,
                'processed_sql': processed_sql
            }

        except Exception as e:
            # 记录错误
            record.error_message = str(e)
            db.commit()

            logger.error(f"指标任务试运行失败: {task.task_code}, 错误: {str(e)}")
            raise

    async def _mock_spark_execution(
        self,
        sql: str,
        etl_date: str,
        sample_size: int,
        indicator_codes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """模拟Spark SQL执行

        实际环境中应该替换为：
        1. 连接Spark ThriftServer (JDBC)
        2. 执行SQL
        3. 获取结果

        Args:
            sql: SQL语句
            etl_date: ETL日期
            sample_size: 样本大小
            indicator_codes: 指标编码列表（用于生成对应字段）

        Returns:
            执行结果
        """
        # 模拟执行延迟
        await asyncio.sleep(2)

        # 模拟生成数据，包含必需的字段
        sample_result = []
        for i in range(min(sample_size, 10)):  # 只返回最多10条样本
            row = {
                'target_id': f'CUST{str(i+1).zfill(8)}',  # 必需字段：target_id
                'etl_date': etl_date,  # 必需字段：etl_date
            }

            # 为每个指标编码生成对应的字段
            if indicator_codes:
                for indicator_code in indicator_codes:
                    # 生成随机指标值
                    import random
                    if indicator_code.endswith('_cnt'):  # 计数类指标
                        row[indicator_code] = str(random.randint(0, 100))
                    elif indicator_code.endswith('_amt'):  # 金额类指标
                        row[indicator_code] = f"{random.uniform(0, 10000):.2f}"
                    elif indicator_code.endswith('_flag'):  # 标志类指标
                        row[indicator_code] = random.choice(['Y', 'N'])
                    elif indicator_code.endswith('_ratio'):  # 比率类指标
                        row[indicator_code] = f"{random.uniform(0, 1):.4f}"
                    else:  # 其他类型指标
                        row[indicator_code] = str(random.randint(1, 10))
            else:
                # 如果没有提供指标编码，使用示例字段
                row['i_dep_acct_no_offline_00005'] = str((i % 5) + 1)
                row['i_dep_acct_no_offline_00006'] = str((i % 3) + 1)

            sample_result.append(row)

        log_content = f"""
[模拟Spark执行日志]
执行时间: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}
ETL日期: {etl_date}
样本大小: {sample_size}

SQL语句:
{sql}

执行结果:
- 读取源表记录数: {sample_size * 10}
- 处理记录数: {sample_size}
- 输出记录数: {sample_size}

注意：这是模拟执行结果，实际生产环境将连接Spark ThriftServer执行真实SQL。
"""

        return {
            'rows_processed': sample_size,
            'rows_output': sample_size,
            'duration_seconds': 2,
            'sample_result': sample_result,
            'log_content': log_content
        }

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

            Args:
                db: 数据库会话
                task_data: 任务数据
                indicator_ids: 关联的指标ID列表
                etl_date: ETL日期，如果为None则使用昨天
                sample_size: 样本大小

            Returns:
                验证结果
            """
            if etl_date is None:
                etl_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

            logger.info(f"开始验证任务逻辑，关联 {len(indicator_ids)} 个指标")

            # 替换SQL中的日期变量
            processed_sql = self._replace_date_variables(task_data.logic_content, etl_date)

            # 获取关联的指标编码
            indicators = db.query(FraudHunterIndicatorDefinition).filter(
                FraudHunterIndicatorDefinition.id.in_(indicator_ids)
            ).all()

            if len(indicators) != len(indicator_ids):
                found_ids = [ind.id for ind in indicators]
                missing_ids = set(indicator_ids) - set(found_ids)
                raise ValueError(f"指标不存在: {missing_ids}")

            indicator_codes = [ind.indicator_code for ind in indicators]

            # 模拟SQL执行
            result = await self._mock_spark_execution(
                processed_sql,
                etl_date,
                sample_size,
                indicator_codes
            )

            # 字段验证
            validation_result = self._validate_output_fields(
                result['sample_result'], indicator_ids, db
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

    async def execute_production(
        self,
        db: Session,
        execution_id: str,
        task_id: int,
        etl_date: str
    ) -> Dict[str, Any]:
        """执行指标任务生产任务（预留）

        实际生产环境中执行完整的指标计算
        此方法目前不实现，预留给后续集成DolphinScheduler时使用

        Args:
            db: 数据库会话
            execution_id: 执行ID
            task_id: 指标任务ID
            etl_date: ETL日期

        Returns:
            执行结果摘要
        """
        raise NotImplementedError("生产任务执行需要集成DolphinScheduler，暂未实现")


# 全局指标执行器实例
indicator_executor = IndicatorExecutor()
