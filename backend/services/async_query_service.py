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
            task_status = await tracker.get_task_status(task_id)
            if not task_status:
                return None

            # 转换为API需要的格式
            result = task_status.to_dict()

            # 确定状态
            if task_status.status == "running":
                result["status"] = "running"
            elif task_status.status in ("success", "completed"):
                result["status"] = "success"
            elif task_status.status == "failed":
                result["status"] = "failed"
            else:
                result["status"] = task_status.status

            # 添加一些兼容字段
            result["current_step"] = task_status.current_step
            result["progress"] = task_status.progress

            return result

        except Exception as e:
            logger.error(f"获取任务结果失败: {e}")
            return None

    async def _execute_query(self, task_id: str, user_input: str, max_retries: int,
                           operator: str, flow_type: str):
        """执行查询任务"""
        try:
            # 调用NL2SQL服务处理查询
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                self.nl2sql_service.process_query,
                user_input,
                task_id,
                max_retries,
                operator,
                flow_type
            )

            # 更新最终状态
            if result.get('success'):
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
                    error=result.get('error', '未知错误'),
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


# 兼容旧API的函数
async def submit_query(user_input: str, operator: str = "api_user",
                      flow_type: str = "fast", max_retries: int = 5) -> str:
    """提交查询任务（兼容函数）"""
    service = get_async_query_service()
    return await service.submit_query(user_input, operator, flow_type, max_retries)


async def get_task_result(task_id: str) -> Optional[Dict[str, Any]]:
    """获取任务结果（兼容函数）"""
    service = get_async_query_service()
    return await service.get_task_result(task_id)