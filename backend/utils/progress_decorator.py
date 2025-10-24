"""
进度跟踪装饰器
用于在LangGraph工作流节点中跟踪进度和详细日志
"""

import asyncio
import functools
from datetime import datetime
from typing import Callable, List

from langgraph.errors import GraphInterrupt

from services.service_models import BaseNodeLog, TaskState
from services.tracking_service.tracker_cache import tracker_cache
from utils.logger import logger


def track_node_progress(node_name: str):
    """
    节点进度跟踪装饰器

    Args:
        node_name: 节点名称，用于显示和进度映射
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(state: TaskState) -> TaskState:
            start_time = datetime.now()
            task_id = state.task_id

            state.current_step_name = f"{node_name} 流程开始"

            # 更新流程开始状态（只更新缓存，不写入数据库）
            if task_id:
                # 直接更新缓存，避免依赖tracker
                cached_state = tracker_cache.get_task_state(task_id)

                if cached_state:
                    cached_state.update({
                        'progress': state.progress,
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
                new_progress = state.progress

                # 只有在进度未达到90时才增加
                if new_progress < 90:
                    if current_step_log.success:
                        # 成功：进度+10，最多到90
                        new_progress = min(new_progress + 10, 90)
                    else:
                        # 失败：进度+5，最多到90
                        new_progress = min(new_progress + 5, 90)

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
            except GraphInterrupt as gi:
                logger.warning('触发GraphInterrupt 异常，等待用户输入')

                cached_state = tracker_cache.get_task_state(task_id)

                cached_state.update({
                    'progress': state.progress,
                    'current_step': f"{node_name} 等待用户输入",
                    'current_step_name': f"{node_name} 等待用户输入",
                    'current_step_log': None,
                    'error_message': state.error_message,
                    'execution_result': state.execution_result or cached_state.get('execution_result'),
                    'waiting_for_user_input': state.waiting_for_user_input,
                    'return_to_node': state.return_to_node,
                    'clear_check_details': state.clear_check_details,
                    'sql_query': state.sql_query or cached_state.get('sql_query')
                })

                tracker_cache.set_task_state(task_id, cached_state)

                raise

            except Exception as e:
                # 异常时也要更新状态
                if task_id:
                    # 直接更新缓存，避免依赖tracker
                    cached_state = tracker_cache.get_task_state(task_id)
                    if cached_state:
                        cached_state.update({
                            'progress': state.progress,
                            'current_step': f"{node_name} 流程失败",
                            'current_step_name': f"{node_name} 流程失败",
                            'error_message': str(e),
                            'status': 'failed'
                        })
                        tracker_cache.set_task_state(task_id, cached_state)
                raise

        return wrapper
    return decorator