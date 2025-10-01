"""
简单的任务缓存系统
"""

import asyncio
import uuid
from typing import Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from utils.logger import logger, get_logger, LoggerMixin


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class TaskResult:
    """任务结果"""
    task_id: str
    user_input: str
    status: TaskStatus
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    current_step: str = "准备中"
    progress: int = 0  # 0-100
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    logs: list = field(default_factory=list)


class SimpleTaskCache(LoggerMixin):
    """简单的任务缓存管理器"""

    def __init__(self):
        super().__init__()
        self.tasks: Dict[str, TaskResult] = {}
        self._lock = asyncio.Lock()

    async def create_task(self, user_input: str) -> str:
        """创建新任务"""
        task_id = str(uuid.uuid4())

        async with self._lock:
            task = TaskResult(
                task_id=task_id,
                user_input=user_input,
                status=TaskStatus.PENDING,
                current_step="任务已创建"
            )
            self.tasks[task_id] = task

        self.logger.info(f"创建任务: {task_id}, 输入: {user_input[:50]}...")
        return task_id

    async def update_task_status(self, task_id: str, status: TaskStatus,
                                current_step: str = None, progress: int = None,
                                result: Dict[str, Any] = None, error: str = None,
                                log_message: Dict[str, Any] = None):
        """更新任务状态"""
        async with self._lock:
            if task_id not in self.tasks:
                self.logger.warning(f"任务不存在: {task_id}")
                return

            task = self.tasks[task_id]
            task.status = status

            if status == TaskStatus.RUNNING and task.started_at is None:
                task.started_at = datetime.now()

            if status in [TaskStatus.SUCCESS, TaskStatus.FAILED]:
                task.completed_at = datetime.now()

            if current_step:
                task.current_step = current_step

            if progress is not None:
                task.progress = progress

            if result:
                task.result = result

            if error:
                task.error = error

            if log_message:
                
                self.logger.info(f"步骤的日志：{log_message}")
                
                task.logs.append({
                    "timestamp": datetime.now().isoformat(),
                    "step": log_message["step"],
                    "input_data": log_message['input_data'],
                    "prompt": log_message["prompt"],
                    "model_output": log_message["model_output"],
                    "error": log_message["error"]
                })

        self.logger.info(f"更新任务 {task_id}: {status.value} - {current_step}")

    async def get_task(self, task_id: str) -> Optional[TaskResult]:
        """获取任务信息"""
        async with self._lock:
            return self.tasks.get(task_id)

    async def get_all_tasks(self) -> list[TaskResult]:
        """获取所有任务（按创建时间倒序）"""
        async with self._lock:
            return sorted(self.tasks.values(), key=lambda x: x.created_at, reverse=True)

    async def clean_old_tasks(self, max_age_hours: int = 24):
        """清理旧任务"""
        from datetime import timedelta

        async with self._lock:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            old_tasks = [
                task_id for task_id, task in self.tasks.items()
                if task.created_at < cutoff_time
            ]

            for task_id in old_tasks:
                del self.tasks[task_id]

        if old_tasks:
            self.logger.info(f"清理了 {len(old_tasks)} 个旧任务")


# 全局实例
_task_cache = None

def get_task_cache() -> SimpleTaskCache:
    """获取任务缓存实例"""
    global _task_cache
    if _task_cache is None:
        _task_cache = SimpleTaskCache()
    return _task_cache