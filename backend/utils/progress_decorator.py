"""
进度跟踪装饰器
用于在LangGraph工作流节点中跟踪进度和详细日志
"""

import functools
from datetime import datetime
from typing import Dict, Any, Callable, List, Optional

from services.nl2sql_service import BaseNodeLog
from utils.logger import get_logger


def calculate_progress_from_logs(logs: List[Dict[str, Any]]) -> int:
    """
    从日志列表中计算当前进度

    Args:
        logs: 日志列表，每个日志包含success字段

    Returns:
        当前进度百分比
    """
    progress = 10

    for log in logs:
        if log.get('success'):
            # 成功的节点：+10进度，最多到90
            progress = min(progress + 10, 90)
        elif log.get('success') is False:
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

            state.current_step_name = f"{node_name} 流程开始"
            state.current_progress = current_progress

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

                result_state.current_step_name = f"{node_name} 流程结束"
                result_state.current_progress = new_progress
                return result_state

            except Exception as e:
                raise

        return wrapper
    return decorator