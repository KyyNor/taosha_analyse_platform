"""
进度跟踪装饰器
用于在LangGraph工作流节点中跟踪进度和详细日志
"""

import asyncio
import functools
from datetime import datetime
from typing import Dict, Any, Callable, List

from services.service_models import BaseNodeLog, TaskState
from services.operation_tracking import tracker


def safe_create_async_task(coro):
    """安全地创建异步任务，支持同步和异步环境"""
    try:
        loop = asyncio.get_running_loop()
        return loop.create_task(coro)
    except RuntimeError:
        # 没有运行的事件循环，创建新的
        try:
            return asyncio.run(coro)
        except RuntimeError:
            # 如果还是失败，尝试在新的事件循环中运行
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                return executor.submit(asyncio.run, coro)


def calculate_progress_from_logs(logs: List[BaseNodeLog]) -> int:
    """
    从日志列表中计算当前进度

    Args:
        logs: 日志列表，每个日志包含success字段

    Returns:
        当前进度百分比
    """
    progress = 10

    for log in logs:
        if log.success:
            # 成功的节点：+10进度，最多到90
            progress = min(progress + 10, 90)
        else:
            # 失败的节点：+5进度，最多到90
            progress = min(progress + 5, 90)

    return progress


def track_node_progress(node_name: str):
    """
    节点进度跟踪装饰器

    Args:
        node_name: 节点名称，用于显示和进度映射
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(state: Dict[str, Any]) -> Dict[str, Any]:
            # 获取现有的日志列表
            logs = state.get('logs', [])

            # 从历史日志计算当前进度
            current_progress = calculate_progress_from_logs(logs)
            start_time = datetime.now()
            task_id = state.get('task_id')

            state['current_step_name'] = f"{node_name} 流程开始"
            state['current_progress'] = current_progress

            try:
                # 执行原函数
                result_state = func(state)
                current_step_log: BaseNodeLog = result_state['current_step_log']

                current_step_log.start_time = start_time
                current_step_log.end_time = datetime.now()

                # 计算新的进度
                new_progress = current_progress

                # 只有在进度未达到90时才增加
                if current_progress < 90:
                    if current_step_log.success:
                        # 成功：进度+10，最多到90
                        new_progress = min(current_progress + 10, 90)
                    else:
                        # 失败：进度+5，最多到90
                        new_progress = min(current_progress + 5, 90)

                # 特殊处理最后完成节点
                if node_name == '执行查询语句' and current_step_log.success == True:
                    new_progress = 100

                # 更新追踪系统
                if task_id:
                    # 异步更新任务状态，不阻塞主流程
                    safe_create_async_task(
                        tracker.update_task_progress(
                            task_id=task_id,
                            progress=new_progress,
                            step_name=f"{node_name} 流程结束",
                            logs=[{
                                "step_name": node_name,
                                "input_data": current_step_log.input_data,
                                "output_data": current_step_log.model_output,
                                "success": current_step_log.success,
                                "error": current_step_log.error,
                                "timestamp": current_step_log.end_time.isoformat() if current_step_log.end_time else datetime.now().isoformat()
                            }],
                            error=current_step_log.error if not current_step_log.success else None,
                            final_status="success" if new_progress == 100 else None
                        )
                    )

                result_state['current_step_name'] = f"{node_name} 流程结束"
                result_state['current_progress'] = new_progress
                return result_state

            except Exception as e:
                # 异常时也要更新状态
                if task_id:
                    safe_create_async_task(
                        tracker.update_task_progress(
                            task_id=task_id,
                            progress=current_progress,
                            step_name=f"{node_name} 流程失败",
                            error=str(e),
                            final_status="failed"
                        )
                    )
                raise

        return wrapper
    return decorator