"""
操作追踪服务 - 简化版本，支持缓存和状态管理
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from cachetools import TTLCache
from utils.logger import logger
from utils.db_utils import get_database_manager


@dataclass
class TaskStatus:
    """任务状态数据"""
    task_id: str
    user_input: str
    status: str  # 'running', 'success', 'failed'
    current_step: str
    progress: int
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    logs: List[Dict[str, Any]] = None
    operator: Optional[str] = None
    flow_type: Optional[str] = None

    def __post_init__(self):
        if self.logs is None:
            self.logs = []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        data = asdict(self)
        # 转换datetime为ISO格式字符串
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
        return data


class TaskCache:
    """任务状态缓存管理 - 使用 cachetools"""

    def __init__(self, max_size: int = 100, ttl_seconds: int = 24 * 3600):
        self._cache = TTLCache(maxsize=max_size, ttl=ttl_seconds)
        logger.info(f"任务缓存初始化完成: max_size={max_size}, ttl={ttl_seconds}秒")

    async def get(self, task_id: str) -> Optional[TaskStatus]:
        """获取缓存中的任务状态"""
        try:
            return self._cache.get(task_id)
        except Exception as e:
            logger.error(f"从缓存获取任务状态失败: {e}")
            return None

    async def set(self, task_id: str, status: TaskStatus):
        """设置任务状态到缓存"""
        try:
            self._cache[task_id] = status
        except Exception as e:
            logger.error(f"设置任务状态到缓存失败: {e}")

    async def remove(self, task_id: str):
        """从缓存中删除任务"""
        try:
            self._cache.pop(task_id, None)
        except Exception as e:
            logger.error(f"从缓存删除任务失败: {e}")

    def clear(self):
        """清空缓存"""
        try:
            self._cache.clear()
            logger.info("任务缓存已清空")
        except Exception as e:
            logger.error(f"清空缓存失败: {e}")

    def info(self) -> Dict[str, Any]:
        """获取缓存信息"""
        try:
            return {
                "maxsize": self._cache.maxsize,
                "currsize": len(self._cache),
                "ttl": getattr(self._cache, 'ttl', 'N/A')
            }
        except Exception as e:
            logger.error(f"获取缓存信息失败: {e}")
            return {}


class OperationTracker:
    """简化的操作追踪器"""

    def __init__(self):
        self.db_manager = get_database_manager()
        self.cache = TaskCache()

    async def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """获取任务状态（先查缓存，再查数据库）"""
        # 先查缓存
        cached_status = await self.cache.get(task_id)
        if cached_status:
            return cached_status

        # 缓存未命中，查询数据库
        try:
            row = self.db_manager.execute_query("""
                SELECT s.*,
                       CASE WHEN s.status = 'running' THEN 'running'
                            WHEN s.error_message IS NOT NULL THEN 'failed'
                            ELSE 'completed' END as final_status
                FROM operation_sessions s
                WHERE s.session_id = ?
            """, (task_id,), fetch="one")

            if not row:
                return None

            # 查询步骤日志
            steps = self.db_manager.execute_query("""
                SELECT step_sequence, step_name, input_data, output_data,
                       generated_sql, error_message, success, created_at
                FROM operation_steps
                WHERE session_id = ?
                ORDER BY step_sequence
            """, (task_id,))

            # 构建任务状态
            status = TaskStatus(
                task_id=row[0],  # session_id
                user_input="",  # 需要从步骤日志中获取
                status=row[1] if row[1] != 'running' else 'running',
                current_step="",  # 从最新步骤获取
                progress=100 if row[1] in ('completed', 'failed') else 90,
                created_at=datetime.fromisoformat(row[2]),
                started_at=datetime.fromisoformat(row[2]) if row[2] else None,
                completed_at=datetime.fromisoformat(row[3]) if row[3] else None,
                result=None,  # 需要从最终结果获取
                error=row[4],
                logs=[
                    {
                        "step_sequence": step[0],
                        "step_name": step[1],
                        "input_data": step[2],
                        "output_data": step[3],
                        "generated_sql": step[4],
                        "error_message": step[5],
                        "success": bool(step[6]),
                        "timestamp": step[7]
                    }
                    for step in steps
                ]
            )

            # 更新缓存
            await self.cache.set(task_id, status)
            return status

        except Exception as e:
            logger.error(f"从数据库获取任务状态失败: {e}")
            return None

    async def update_task_progress(self, task_id: str, progress: int,
                                 step_name: str, logs: List[Dict[str, Any]] = None,
                                 error: str = None, final_status: str = None):
        """更新任务进度（更新缓存，异步写数据库）"""
        # 获取或创建任务状态
        status = await self.cache.get(task_id)
        if not status:
            status = TaskStatus(
                task_id=task_id,
                user_input="",
                status="running",
                current_step=step_name,
                progress=progress,
                created_at=datetime.now()
            )

        # 更新状态
        status.progress = progress
        status.current_step = step_name
        if logs:
            status.logs.extend(logs)
        if error:
            status.error = error
            status.status = "failed"
            status.completed_at = datetime.now()
        elif final_status:
            status.status = final_status
            if final_status in ("success", "completed"):
                status.completed_at = datetime.now()
                status.progress = 100

        # 更新缓存
        await self.cache.set(task_id, status)

        # 写入数据库
        await self._write_to_db(status)

    async def create_task(self, task_id: str, user_input: str,
                         operator: str = None, flow_type: str = None):
        """创建新任务"""
        status = TaskStatus(
            task_id=task_id,
            user_input=user_input,
            status="running",
            current_step="初始化",
            progress=0,
            created_at=datetime.now(),
            started_at=datetime.now(),
            operator=operator,
            flow_type=flow_type
        )

        # 更新缓存
        await self.cache.set(task_id, status)

        await self._write_session_to_db(task_id, operator)

    async def _write_to_db(self, status: TaskStatus):
        """异步写入任务状态到数据库"""
        try:
            # 更新会话状态
            self.db_manager.execute_query("""
                UPDATE operation_sessions
                SET status = ?, end_time = ?, error_message = ?, updated_at = ?
                WHERE session_id = ?
            """, (
                status.status,
                status.completed_at.isoformat() if status.completed_at else None,
                status.error,
                datetime.now().isoformat(),
                status.task_id
            ))

            # 写入步骤日志（只写入最新的一条）
            if status.logs:
                latest_log = status.logs[-1]
                self.db_manager.execute_query("""
                    INSERT INTO operation_steps
                    (session_id, step_sequence, step_name, input_data,
                     output_data, generated_sql, error_message, success,
                     token_usage, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    status.task_id,
                    latest_log.get("step_sequence", len(status.logs)),
                    latest_log.get("step_name", ""),
                    latest_log.get("input_data", ""),
                    latest_log.get("output_data", ""),
                    latest_log.get("generated_sql", ""),
                    latest_log.get("error_message", ""),
                    latest_log.get("success", True),
                    "{}",  # token_usage
                    "{}"   # metadata
                ))

            logger.debug(f"任务 {status.task_id} 状态已写入数据库")

        except Exception as e:
            logger.error(f"写入任务 {status.task_id} 到数据库失败: {e}")

    async def _write_session_to_db(self, task_id: str, operator: str = None):
        """异步写入会话记录到数据库"""
        try:
            self.db_manager.execute_query("""
                INSERT INTO operation_sessions
                (session_id, operation_type, operator, start_time, status)
                VALUES (?, ?, ?, ?, ?)
            """, (task_id, "nl2sql_query", operator, datetime.now().isoformat(), 'running'))
        except Exception as e:
            logger.error(f"创建会话记录失败: {e}")


# 全局追踪器实例
tracker = OperationTracker()