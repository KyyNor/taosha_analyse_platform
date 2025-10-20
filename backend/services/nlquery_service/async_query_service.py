"""
异步查询服务
"""

import asyncio
import uuid
from typing import Optional, Set
from utils.logger import logger
from services.tracking_service.operation_tracking import OperationTracker
from models.db_base import get_db, SessionLocal
from .nl2sql_service import get_nl2sql_service


_background_tasks: Set[asyncio.Task] = set()


class AsyncQueryService:
    """异步查询服务类"""

    def __init__(self):
        """初始化异步查询服务
        """
        # 使用新的模块化架构
        db_session = SessionLocal()
        self.nl2sql_service = get_nl2sql_service(db_session=db_session)
        logger.info("AsyncQueryService 使用 NL2SQLServiceV2（新的模块化架构）")

    async def submit_query(self, user_input: str, operator: str = "api_user",
                          flow_type: str = "fast", max_retries: int = 5, tracker: OperationTracker = None) -> str:
        """提交查询任务"""
        if tracker is None:
            raise ValueError("tracker参数是必须的，请通过依赖注入传入OperationTracker实例")

        # 创建任务
        task_id = str(uuid.uuid4())

        # 启动后台任务，传递tracker实例
        task = asyncio.create_task(
            self._execute_query(task_id, user_input, max_retries, operator, flow_type, tracker)
        )
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)
        task.add_done_callback(lambda t: self._log_task_result(t, task_id))

        return task_id

    # async def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
    #     """获取任务结果"""
    #     try:
    #         # 从追踪系统获取任务状态
    #         task_state = await tracker.get_task_status(task_id)
    #         if not task_state:
    #             return None
    #
    #         # 使用统一的 to_dict 方法转换为API格式
    #         result = task_state.model_dump()
    #
    #         return result
    #
    #     except Exception as e:
    #         logger.error(f"获取任务结果失败: {e}")
    #         return None

    async def _execute_query(self, task_id: str, user_input: str, max_retries: int,
                           operator: str, flow_type: str, tracker: OperationTracker):
        """执行查询任务"""
        try:

            # 获取事件循环
            loop = asyncio.get_event_loop()

            # 将同步的NL2SQL处理移到线程池执行，避免阻塞事件循环
            await loop.run_in_executor(
                None,  # 使用默认线程池
                self.nl2sql_service.process_query,
                user_input, task_id, max_retries, operator, flow_type, tracker
            )

            # 从全局缓存获取结果
            from services.tracking_service.tracker_cache import tracker_cache
            cached_state = tracker_cache.get_task_state(task_id)

            if cached_state:
                # 更新最终状态 - 只更新会话状态，不添加新的步骤日志
                if cached_state.get('status') in ('success', 'completed'):
                    await tracker.update_task_progress(
                        task_id=task_id,
                        progress=100,
                        step_name="查询完成",
                        final_status="success",
                        write_step_log=False  # 不写入步骤日志，避免重复记录
                    )
                else:
                    await tracker.update_task_progress(
                        task_id=task_id,
                        progress=0,
                        step_name="查询失败",
                        error=cached_state.get('error_message') or '未知错误',
                        final_status="failed",
                        write_step_log=False  # 不写入步骤日志，避免重复记录
                    )

        except Exception as e:
            logger.error(f"执行查询任务失败: {e}")
            await tracker.update_task_progress(
                task_id=task_id,
                progress=0,
                step_name="查询异常",
                error=str(e),
                final_status="failed",
                write_step_log=False  # 不写入步骤日志，避免重复记录
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
    """获取异步查询服务实例

    Returns:
        AsyncQueryService实例
    """
    global _async_query_service
    if _async_query_service is None:
        _async_query_service = AsyncQueryService()
    return _async_query_service
