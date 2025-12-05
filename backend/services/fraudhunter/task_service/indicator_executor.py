"""
指标执行器（模拟Spark SQL执行）
"""

import asyncio
from typing import Dict, Any
from datetime import datetime, date
from sqlalchemy.orm import Session
from models.fraudhunter.indicator import FraudHunterIndicatorTask
from models.fraudhunter.task import FraudHunterTaskExecutionRecord
from utils.logger import logger


class IndicatorExecutor:
    """指标执行器

    由于实际Spark环境尚未集成，此处提供模拟执行功能
    """

    async def execute_dry_run(
        self,
        db: Session,
        execution_id: str,
        task_id: int,
        etl_date: str,
        sample_size: int = 100,
        task_version: int = None
    ) -> Dict[str, Any]:
        """执行指标任务试运行（模拟）

        Args:
            db: 数据库会话
            execution_id: 执行ID
            task_id: 指标任务ID
            etl_date: ETL日期
            sample_size: 样本大小
            task_version: 指标任务版本号（可选）

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
            # 模拟SQL执行（实际应该调用Spark JDBC连接执行）
            result = await self._mock_spark_execution(
                task.logic_content,
                etl_date,
                sample_size
            )

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
                'execution_time_seconds': result['duration_seconds']
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
        sample_size: int
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

        Returns:
            执行结果
        """
        # 模拟执行延迟
        await asyncio.sleep(2)

        # 模拟生成数据
        sample_result = []
        for i in range(min(sample_size, 10)):  # 只返回最多10条样本
            sample_result.append({
                'account_id': f'ACC{str(i+1).zfill(6)}',
                'indicator_code': 'i_login_cnt_7d',
                'indicator_value': str((i % 5) + 1),
                'dt': etl_date.replace('-', '')
            })

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
