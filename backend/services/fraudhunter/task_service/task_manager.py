"""
异步任务管理器
"""

import uuid
import asyncio
from typing import Dict, Optional, Callable, Any
from datetime import datetime
from sqlalchemy.orm import Session
from backend.models.fraudhunter.task import FraudHunterTaskExecution
from backend.database.db_base import get_db_session
from utils.logger import logger


class TaskManager:
    """异步任务管理器"""

    def __init__(self):
        self.running_tasks: Dict[str, asyncio.Task] = {}

    async def submit_task(
        self,
        db: Session,
        task_type: str,
        task_id: int,
        task_func: Callable,
        created_by: str,
        **kwargs
    ) -> str:
        """提交异步任务

        Args:
            db: 数据库会话
            task_type: 任务类型（indicator/model）
            task_id: 任务关联ID
            task_func: 任务执行函数
            created_by: 创建人
            **kwargs: 传递给任务函数的参数

        Returns:
            execution_id: 任务执行ID
        """
        # 生成任务ID
        execution_id = f"task_{uuid.uuid4()}"

        # 创建任务记录
        task_execution = FraudHunterTaskExecution(
            task_type=task_type,
            task_id=task_id,
            execution_id=execution_id,
            status='pending',
            created_by=created_by
        )

        db.add(task_execution)
        db.commit()

        # 创建异步任务
        task = asyncio.create_task(
            self._run_task(execution_id, task_func, **kwargs)
        )
        self.running_tasks[execution_id] = task

        logger.info(f"任务已提交: {execution_id}, 类型: {task_type}")
        return execution_id

    async def _run_task(self, execution_id: str, task_func: Callable, **kwargs) -> None:
        """执行任务

        Args:
            execution_id: 任务执行ID
            task_func: 任务执行函数
            **kwargs: 传递给任务函数的参数
        """
        with get_db_session() as db:
            try:
                # 更新任务状态为运行中
                task_execution = db.query(FraudHunterTaskExecution).filter(
                    FraudHunterTaskExecution.execution_id == execution_id
                ).first()

                if not task_execution:
                    logger.error(f"任务记录不存在: {execution_id}")
                    return

                task_execution.status = 'running'
                task_execution.start_time = datetime.utcnow()
                db.commit()

                logger.info(f"开始执行任务: {execution_id}")

                # 执行任务
                result = await task_func(db, execution_id, **kwargs)

                # 更新任务状态为成功
                task_execution.status = 'success'
                task_execution.end_time = datetime.utcnow()
                task_execution.result_summary = result
                db.commit()

                logger.info(f"任务执行成功: {execution_id}")

            except Exception as e:
                # 更新任务状态为失败
                task_execution = db.query(FraudHunterTaskExecution).filter(
                    FraudHunterTaskExecution.execution_id == execution_id
                ).first()

                if task_execution:
                    task_execution.status = 'failed'
                    task_execution.end_time = datetime.utcnow()
                    task_execution.result_summary = {
                        'error': str(e),
                        'error_type': type(e).__name__
                    }
                    db.commit()

                logger.error(f"任务执行失败: {execution_id}, 错误: {str(e)}", exc_info=True)

            finally:
                # 清理任务记录
                if execution_id in self.running_tasks:
                    del self.running_tasks[execution_id]

    def get_task_progress(self, db: Session, execution_id: str) -> Dict[str, Any]:
        """获取任务进度

        Args:
            db: 数据库会话
            execution_id: 任务执行ID

        Returns:
            任务进度信息

        Raises:
            ValueError: 如果任务不存在
        """
        task_execution = db.query(FraudHunterTaskExecution).filter(
            FraudHunterTaskExecution.execution_id == execution_id
        ).first()

        if not task_execution:
            raise ValueError(f"任务不存在: {execution_id}")

        # 计算进度（简化版本，实际应该根据任务类型和状态计算）
        progress = 0.0
        if task_execution.status == 'pending':
            progress = 0.0
        elif task_execution.status == 'running':
            progress = 50.0  # 模拟进度
        elif task_execution.status in ['success', 'failed', 'cancelled']:
            progress = 100.0

        # 估算剩余时间（简化版本）
        estimated_remaining_seconds = None
        if task_execution.status == 'running' and task_execution.start_time:
            elapsed = (datetime.utcnow() - task_execution.start_time).total_seconds()
            if progress > 0 and progress < 100:
                estimated_remaining_seconds = int(elapsed * (100 - progress) / progress)

        return {
            'task_id': execution_id,
            'task_type': task_execution.task_type,
            'status': task_execution.status,
            'progress': progress,
            'current_step': self._get_current_step(task_execution.status),
            'start_time': task_execution.start_time,
            'end_time': task_execution.end_time,
            'estimated_remaining_seconds': estimated_remaining_seconds
        }

    def get_task_result(self, db: Session, execution_id: str) -> Dict[str, Any]:
        """获取任务结果

        Args:
            db: 数据库会话
            execution_id: 任务执行ID

        Returns:
            任务结果信息

        Raises:
            ValueError: 如果任务不存在或未完成
        """
        task_execution = db.query(FraudHunterTaskExecution).filter(
            FraudHunterTaskExecution.execution_id == execution_id
        ).first()

        if not task_execution:
            raise ValueError(f"任务不存在: {execution_id}")

        if task_execution.status not in ['success', 'failed']:
            raise ValueError(f"任务尚未完成: {execution_id}")

        # 计算执行时长
        duration_seconds = None
        if task_execution.start_time and task_execution.end_time:
            duration_seconds = int((task_execution.end_time - task_execution.start_time).total_seconds())

        return {
            'task_id': execution_id,
            'status': task_execution.status,
            'duration_seconds': duration_seconds,
            'result': task_execution.result_summary
        }

    async def cancel_task(self, db: Session, execution_id: str) -> bool:
        """取消任务

        Args:
            db: 数据库会话
            execution_id: 任务执行ID

        Returns:
            是否成功取消

        Raises:
            ValueError: 如果任务不存在
        """
        task_execution = db.query(FraudHunterTaskExecution).filter(
            FraudHunterTaskExecution.execution_id == execution_id
        ).first()

        if not task_execution:
            raise ValueError(f"任务不存在: {execution_id}")

        # 尝试取消异步任务
        if execution_id in self.running_tasks:
            task = self.running_tasks[execution_id]
            task.cancel()

            # 更新任务状态
            task_execution.status = 'cancelled'
            task_execution.end_time = datetime.utcnow()
            db.commit()

            logger.info(f"任务已取消: {execution_id}")
            return True

        # 如果任务还在pending状态，直接标记为cancelled
        if task_execution.status == 'pending':
            task_execution.status = 'cancelled'
            task_execution.end_time = datetime.utcnow()
            db.commit()
            logger.info(f"任务已取消: {execution_id}")
            return True

        return False

    def list_task_executions(
        self,
        db: Session,
        task_type: Optional[str] = None,
        task_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[list, int]:
        """查询任务执行历史

        Args:
            db: 数据库会话
            task_type: 任务类型筛选
            task_id: 任务ID筛选
            page: 页码
            page_size: 每页数量

        Returns:
            (任务列表, 总数)
        """
        query = db.query(FraudHunterTaskExecution)

        if task_type:
            query = query.filter(FraudHunterTaskExecution.task_type == task_type)

        if task_id:
            query = query.filter(FraudHunterTaskExecution.task_id == task_id)

        total = query.count()
        offset = (page - 1) * page_size
        items = query.order_by(FraudHunterTaskExecution.created_at.desc()).offset(offset).limit(page_size).all()

        return items, total

    def _get_current_step(self, status: str) -> str:
        """根据状态获取当前步骤描述

        Args:
            status: 任务状态

        Returns:
            步骤描述
        """
        step_map = {
            'pending': '等待执行',
            'running': '正在执行',
            'success': '执行成功',
            'failed': '执行失败',
            'cancelled': '已取消'
        }
        return step_map.get(status, '未知状态')


# 全局任务管理器实例
task_manager = TaskManager()
