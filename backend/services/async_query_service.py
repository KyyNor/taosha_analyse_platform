"""
异步查询服务
"""

import asyncio
from typing import Dict, Any, Optional
from utils.logger import get_logger, LoggerMixin
from utils.task_cache import get_task_cache, TaskStatus
from services import get_nl2sql_service


class AsyncQueryService(LoggerMixin):
    """异步查询服务"""

    def __init__(self):
        super().__init__()
        self.task_cache = get_task_cache()

    async def submit_query(self, user_input: str, operator: str = "api_user",
                          flow_type: str = "fast", max_retries: int = 5) -> str:
        """提交查询任务"""
        # 创建任务
        task_id = await self.task_cache.create_task(user_input)

        # 启动后台任务
        asyncio.create_task(
            self._execute_query_task(task_id, user_input, operator, flow_type, max_retries)
        )

        return task_id

    async def _execute_query_task(self, task_id: str, user_input: str, operator: str,
                                 flow_type: str, max_retries: int):
        """执行查询任务"""
        try:
            # 更新状态为运行中
            await self.task_cache.update_task_status(
                task_id, TaskStatus.RUNNING, current_step="开始处理查询", progress=10
            )

            # 获取NL2SQL服务
            nl2sql_service = get_nl2sql_service()

            # 创建进度回调函数
            def progress_callback(step_name: str, message: str, progress: int):
                self.logger.info(f"进度更新: {step_name} - {message} ({progress}%)")
                try:
                    loop = asyncio.get_running_loop()
                    # 如果在事件循环中，直接创建任务
                    asyncio.create_task(
                        self.task_cache.update_task_status(
                            task_id, TaskStatus.RUNNING,
                            current_step=f"{step_name}: {message}",
                            progress=progress,
                            log_message=f"{step_name}: {message}"
                        )
                    )
                except RuntimeError:
                    # 如果没有运行的事件循环，使用asyncio.run来执行
                    async def update_status():
                        await self.task_cache.update_task_status(
                            task_id, TaskStatus.RUNNING,
                            current_step=f"{step_name}: {message}",
                            progress=progress,
                            log_message=f"{step_name}: {message}"
                        )
                    asyncio.run(update_status())

            # 处理查询 - 在线程池中运行同步方法以避免阻塞事件循环
            import concurrent.futures
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # 如果没有运行的事件循环，创建一个新的事件循环
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            with concurrent.futures.ThreadPoolExecutor() as executor:
                result = await loop.run_in_executor(
                    executor,
                    nl2sql_service.process_query,
                    user_input,
                    max_retries,
                    operator,
                    flow_type,
                    progress_callback
                )

            # 任务完成
            await self.task_cache.update_task_status(
                task_id, TaskStatus.SUCCESS,
                current_step="查询完成",
                progress=100,
                result=result,
                log_message="查询执行成功"
            )

        except Exception as e:
            error_message = f"查询执行失败: {str(e)}"
            self.logger.error(error_message, exc_info=True)

            await self.task_cache.update_task_status(
                task_id, TaskStatus.FAILED,
                current_step="查询失败",
                error=error_message,
                log_message=error_message
            )

    async def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务结果"""
        task = await self.task_cache.get_task(task_id)
        if not task:
            return None

        return {
            'task_id': task.task_id,
            'user_input': task.user_input,
            'status': task.status.value,
            'current_step': task.current_step,
            'progress': task.progress,
            'created_at': task.created_at.isoformat(),
            'started_at': task.started_at.isoformat() if task.started_at else None,
            'completed_at': task.completed_at.isoformat() if task.completed_at else None,
            'result': task.result,
            'error': task.error,
            'logs': task.logs
        }

    async def get_all_tasks(self) -> list[Dict[str, Any]]:
        """获取所有任务"""
        tasks = await self.task_cache.get_all_tasks()
        return [
            {
                'task_id': task.task_id,
                'user_input': task.user_input,
                'status': task.status.value,
                'current_step': task.current_step,
                'progress': task.progress,
                'created_at': task.created_at.isoformat(),
                'started_at': task.started_at.isoformat() if task.started_at else None,
                'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                'has_result': task.result is not None,
                'has_error': task.error is not None
            }
            for task in tasks
        ]


# 全局实例
_async_query_service = None

def get_async_query_service() -> AsyncQueryService:
    """获取异步查询服务实例"""
    global _async_query_service
    if _async_query_service is None:
        _async_query_service = AsyncQueryService()
    return _async_query_service