"""
异步查询服务
"""

import asyncio
import uuid
from typing import Dict, Any, Optional, Set
from utils.logger import logger
from services import get_nl2sql_service


_background_tasks: Set[asyncio.Task] = set()

async def submit_query(self, user_input: str, operator: str = "api_user",
                      flow_type: str = "fast", max_retries: int = 5) -> str:
    """提交查询任务"""
    # 创建任务
    task_id = str(uuid.uuid4())
    nl2sql_service = get_nl2sql_service()

    # 启动后台任务
    task = asyncio.create_task(
        nl2sql_service.process_query(user_input, task_id, max_retries, operator, flow_type)
    )
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    task.add_done_callback(_log_task_result)

    return task_id

def _log_task_result(t: asyncio.Task) -> None:
    try:
        t.result()               # 把异常重新抛出
    except Exception as e:
        logger.exception("后台任务失败: %s", e)

# async def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
#     """获取任务结果"""
#     task = await self.task_cache.get_task(task_id)
#     if not task:
#         return None
#
#     return {
#         'task_id': task.task_id,
#         'user_input': task.user_input,
#         'status': task.status.value,
#         'current_step': task.current_step,
#         'progress': task.progress,
#         'created_at': task.created_at.isoformat(),
#         'started_at': task.started_at.isoformat() if task.started_at else None,
#         'completed_at': task.completed_at.isoformat() if task.completed_at else None,
#         'result': task.result,
#         'error': task.error,
#         'logs': task.logs
#     }
