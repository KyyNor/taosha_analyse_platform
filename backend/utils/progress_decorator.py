"""
进度跟踪装饰器
用于在LangGraph工作流节点中跟踪进度和详细日志
"""

import asyncio
import functools
from datetime import datetime
from typing import Callable, List

from services.service_models import BaseNodeLog, TaskState
from services.tracking_service.tracker_cache import tracker_cache


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
        def wrapper(state: TaskState) -> TaskState:
            # 获取现有的日志列表
            logs = state.logs

            # 从历史日志计算当前进度
            progress = calculate_progress_from_logs(logs)
            start_time = datetime.now()
            task_id = state.task_id

            state.current_step_name = f"{node_name} 流程开始"
            state.progress = progress

            # 更新流程开始状态（只更新缓存，不写入数据库）
            if task_id:
                # 直接更新缓存，避免依赖tracker
                cached_state = tracker_cache.get_task_state(task_id)
                if cached_state:
                    cached_state.update({
                        'progress': progress,
                        'current_step': f"{node_name} 流程开始",
                        'current_step_name': f"{node_name} 流程开始"
                    })
                    tracker_cache.set_task_state(task_id, cached_state)

            try:
                # 执行原函数
                result_state = func(state)
                current_step_log: BaseNodeLog = result_state.current_step_log

                current_step_log.start_time = start_time
                current_step_log.end_time = datetime.now()

                # 计算新的进度
                new_progress = progress

                # 只有在进度未达到90时才增加
                if progress < 90:
                    if current_step_log.success:
                        # 成功：进度+10，最多到90
                        new_progress = min(progress + 10, 90)
                    else:
                        # 失败：进度+5，最多到90
                        new_progress = min(progress + 5, 90)

                # 特殊处理最后完成节点
                if node_name == '执行查询语句' and current_step_log.success == True:
                    new_progress = 100

                # 更新缓存系统
                if task_id:
                    # 直接更新缓存，避免依赖tracker
                    cached_state = tracker_cache.get_task_state(task_id)
                    if cached_state:
                        # 添加步骤日志
                        if 'logs' not in cached_state:
                            cached_state['logs'] = []
                        # BaseNodeLog是dataclass，使用__dict__转换为字典
                        cached_state['logs'].append(current_step_log.__dict__)

                        # 更新状态 - 不覆盖 status，让上层决定
                        # status 将由 tracker.update_task_progress() 最终决定
                        cached_state.update({
                            'progress': new_progress,
                            'current_step': f"{node_name} 流程结束",
                            'current_step_name': f"{node_name} 流程结束",
                            'current_step_log': current_step_log.__dict__,
                            'error_message': current_step_log.error if not current_step_log.success else None,
                            'execution_result': state.execution_result or cached_state.get('execution_result'),
                            'sql_query': state.sql_query or cached_state.get('sql_query')
                        })

                        tracker_cache.set_task_state(task_id, cached_state)

                result_state.current_step_name = f"{node_name} 流程结束"
                result_state.progress = new_progress
                return result_state

            except Exception as e:
                # 异常时也要更新状态
                if task_id:
                    # 直接更新缓存，避免依赖tracker
                    cached_state = tracker_cache.get_task_state(task_id)
                    if cached_state:
                        cached_state.update({
                            'progress': progress,
                            'current_step': f"{node_name} 流程失败",
                            'current_step_name': f"{node_name} 流程失败",
                            'error_message': str(e),
                            'status': 'failed'
                        })
                        tracker_cache.set_task_state(task_id, cached_state)
                raise

        return wrapper
    return decorator