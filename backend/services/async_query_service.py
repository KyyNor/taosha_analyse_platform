"""
异步查询服务
"""

import asyncio
import uuid
from typing import Dict, Any, Optional, Set
from utils.logger import logger
from services import get_nl2sql_service
from services.operation_tracking import tracker


_background_tasks: Set[asyncio.Task] = set()


class AsyncQueryService:
    """异步查询服务类"""

    def __init__(self):
        self.nl2sql_service = get_nl2sql_service()

    async def submit_query(self, user_input: str, operator: str = "api_user",
                          flow_type: str = "fast", max_retries: int = 5) -> str:
        """提交查询任务"""
        # 创建任务
        task_id = str(uuid.uuid4())

        # 在追踪系统中创建任务
        await tracker.create_task(
            task_id=task_id,
            user_input=user_input,
            operator=operator,
            flow_type=flow_type
        )

        # 启动后台任务
        task = asyncio.create_task(
            self._execute_query(task_id, user_input, max_retries, operator, flow_type)
        )
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)
        task.add_done_callback(lambda t: self._log_task_result(t, task_id))

        return task_id

    async def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务结果"""
        try:
            # 从追踪系统获取任务状态
            task_state = await tracker.get_task_status(task_id)
            if not task_state:
                return None

            # 使用统一的 to_dict 方法转换为API格式
            result = task_state.to_dict()

            # 确定状态（保持兼容性）
            if task_state.status == "running":
                result["status"] = "running"
            elif task_state.status in ("success", "completed"):
                result["status"] = "success"
            elif task_state.status == "failed":
                result["status"] = "failed"
            else:
                result["status"] = task_state.status

            # 确保有兼容字段
            result.setdefault("current_step", task_state.current_step)
            result.setdefault("progress", task_state.progress)

            return result

        except Exception as e:
            logger.error(f"获取任务结果失败: {e}")
            return None

    async def _execute_query(self, task_id: str, user_input: str, max_retries: int,
                           operator: str, flow_type: str):
        """执行查询任务"""
        try:
            # 获取事件循环
            loop = asyncio.get_event_loop()

            # 将同步的NL2SQL处理移到线程池执行，避免阻塞事件循环
            result = await loop.run_in_executor(
                None,  # 使用默认线程池
                self.nl2sql_service.process_query,
                user_input, task_id, max_retries, operator, flow_type
            )

            # 将结果更新到 OperationTracker 缓存中，确保后续状态更新能找到正确的 TaskState
            await tracker.cache.set(task_id, result)

            # 更新最终状态 - TaskState 对象需要转换为字典或直接访问属性
            if result.status in ('success', 'completed'):
                await tracker.update_task_progress(
                    task_id=task_id,
                    progress=100,
                    step_name="查询完成",
                    final_status="success"
                )
            else:
                await tracker.update_task_progress(
                    task_id=task_id,
                    progress=0,
                    step_name="查询失败",
                    error=result.error_message or '未知错误',
                    final_status="failed"
                )

        except Exception as e:
            logger.error(f"执行查询任务失败: {e}")
            await tracker.update_task_progress(
                task_id=task_id,
                progress=0,
                step_name="查询异常",
                error=str(e),
                final_status="failed"
            )
            raise

    
    def _log_task_result(self, t: asyncio.Task, task_id: str):
        """记录任务结果"""
        try:
            result = t.result()
            logger.info(f"任务 {task_id} 执行完成")
        except Exception as e:
            logger.exception(f"任务 {task_id} 执行失败: {e}")


# 全局服务实例
_async_query_service: Optional[AsyncQueryService] = None


def get_async_query_service() -> AsyncQueryService:
    """获取异步查询服务实例"""
    global _async_query_service
    if _async_query_service is None:
        _async_query_service = AsyncQueryService()
    return _async_query_service
