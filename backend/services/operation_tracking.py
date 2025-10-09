"""
操作追踪服务 - 简化版本，支持缓存和状态管理
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from cachetools import TTLCache
from utils.logger import logger
from utils.db_utils import get_database_manager
from services.service_models import TaskState, BaseNodeLog


class TaskCache:
    """任务状态缓存管理 - 使用 cachetools"""

    def __init__(self, max_size: int = 100, ttl_seconds: int = 24 * 3600):
        self._cache = TTLCache(maxsize=max_size, ttl=ttl_seconds)
        logger.info(f"任务缓存初始化完成: max_size={max_size}, ttl={ttl_seconds}秒")

    async def get(self, task_id: str) -> Optional[TaskState]:
        """获取缓存中的任务状态"""
        try:
            return self._cache.get(task_id)
        except Exception as e:
            logger.error(f"从缓存获取任务状态失败: {e}")
            return None

    async def set(self, task_id: str, state: TaskState):
        """设置任务状态到缓存"""
        try:
            self._cache[task_id] = state
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

    async def get_task_status(self, task_id: str) -> Optional[TaskState]:
        """获取任务状态（先查缓存，再查数据库）"""
        # 先查缓存
        cached_state = await self.cache.get(task_id)
        if cached_state:
            return cached_state

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

            # 构建步骤日志对象
            logs = []
            for step in steps:
                log = BaseNodeLog(
                    step=step[1],
                    input_data=step[2],
                    prompt="",
                    model_output=step[3],
                    success=bool(step[6]),
                    error_message=step[5],
                    start_time=datetime.fromisoformat(step[7]),
                    end_time=datetime.fromisoformat(step[7])
                )
                logs.append(log)

            # 构建任务状态
            state = TaskState(
                task_id=row[0],  # session_id
                user_input="",  # 需要从步骤日志中获取
                status=row[1] if row[1] != 'running' else 'running',
                current_step=steps[-1][1] if steps else "完成",  # 从最新步骤获取
                progress=100 if row[1] in ('completed', 'failed') else 90,
                created_at=datetime.fromisoformat(row[2]),
                started_at=datetime.fromisoformat(row[2]) if row[2] else None,
                completed_at=datetime.fromisoformat(row[3]) if row[3] else None,
                error_message=row[4],
                logs=logs
            )

            # 更新缓存
            await self.cache.set(task_id, state)
            return state

        except Exception as e:
            logger.error(f"从数据库获取任务状态失败: {e}")
            return None

    async def update_task_progress(self, task_id: str, progress: int,
                                 step_name: str, logs: List[Dict[str, Any]] = None,
                                 error: str = None, final_status: str = None):
        """更新任务进度（更新缓存，异步写数据库）"""
        # 获取或创建任务状态
        state = await self.cache.get(task_id)
        if not state:
            state = TaskState(
                task_id=task_id,
                user_input="",
                status="running",
                current_step=step_name,
                progress=progress,
                created_at=datetime.now()
            )

        # 更新状态
        state.progress = progress
        state.current_step = step_name
        state.current_step_name = step_name
        state.current_progress = progress

        if logs:
            # 转换字典日志为BaseNodeLog对象
            for log_dict in logs:
                log = BaseNodeLog(
                    step=log_dict.get("step_name", step_name),
                    input_data=log_dict.get("input_data", ""),
                    prompt="",
                    model_output=log_dict.get("output_data", ""),
                    success=log_dict.get("success", True),
                    error=log_dict.get("error"),
                    start_time=datetime.fromisoformat(log_dict.get("timestamp", datetime.now().isoformat())),
                    end_time=datetime.fromisoformat(log_dict.get("timestamp", datetime.now().isoformat()))
                )
                state.logs.append(log)

        if error:
            state.error_message = error
            state.status = "failed"
            state.completed_at = datetime.now()
        elif final_status:
            state.status = final_status
            if final_status in ("success", "completed"):
                state.completed_at = datetime.now()
                state.progress = 100

        # 更新缓存
        await self.cache.set(task_id, state)

        # 写入数据库
        await self._write_to_db(state)

    async def create_task(self, task_id: str, user_input: str,
                         operator: str = None, flow_type: str = None):
        """创建新任务"""
        state = TaskState(
            task_id=task_id,
            user_input=user_input,
            status="running",
            current_step="初始化",
            progress=0,
            created_at=datetime.now(),
            started_at=datetime.now(),
            operator=operator,
            flow_type=flow_type or "fast"
        )

        # 更新缓存
        await self.cache.set(task_id, state)

        await self._write_session_to_db(task_id, operator)

    async def _write_to_db(self, state: TaskState):
        """异步写入任务状态到数据库"""
        try:
            # 更新会话状态
            self.db_manager.execute_query("""
                UPDATE operation_sessions
                SET status = ?, end_time = ?, error_message = ?, updated_at = ?
                WHERE session_id = ?
            """, (
                state.status,
                state.completed_at.isoformat() if state.completed_at else None,
                state.error_message,
                datetime.now().isoformat(),
                state.task_id
            ))

            # 写入步骤日志（只写入最新的一条）
            if state.logs:
                latest_log = state.current_step_log
                self.db_manager.execute_query("""
                    INSERT INTO operation_steps
                    (session_id, step_sequence, step_name, input_data,
                     output_data, generated_sql, error_message, success,
                     token_usage, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    state.task_id,
                    len(state.logs),
                    latest_log.step,
                    latest_log.input_data,
                    latest_log.model_output,
                    "",  # generated_sql (暂未使用)
                    latest_log.error_message,
                    latest_log.success,
                    "{}",  # token_usage
                    "{}"   # metadata
                ))

            logger.debug(f"任务 {state.task_id} 状态已写入数据库")

        except Exception as e:
            logger.error(f"写入任务 {state.task_id} 到数据库失败: {e}")

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