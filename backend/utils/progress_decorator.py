"""
进度跟踪装饰器
用于在LangGraph工作流节点中跟踪进度和详细日志
"""

import functools
from datetime import datetime
from typing import Dict, Any, Callable, List, Optional
from utils.task_cache import TaskStatus
from utils.logger import get_logger


# class ProgressTracker:
#     """进度跟踪器"""

#     def __init__(self):
#         self.logger = get_logger()

#     def log_node_start(self, node_name: str, input_data: Any, progress_callback: Optional[Callable] = None):
#         """记录节点开始"""
#         start_log = {
#             'node_name': node_name,
#             'status': 'started',
#             'timestamp': datetime.now().isoformat(),
#             'input_data': str(input_data)[:500] if input_data else '',  # 限制长度
#             'message': f'{node_name}流程开始'
#         }

#         if progress_callback:
#             # 根据节点名称映射进度百分比
#             progress_map = {
#                 'check_training': 10,
#                 'validate_input': 30,
#                 'generate_sql': 50,
#                 'execute_sql': 70,
#                 'explain_sql': 85,
#                 'analyze_nl_diff': 95
#             }
#             progress = progress_map.get(node_name, 50)
#             progress_callback(node_name, f'{node_name}流程开始', progress)

#         self.logger.info(f"节点开始: {node_name}")
#         return start_log

#     def log_node_end(self, node_name: str, state: Dict[str, Any], progress_callback: Optional[Callable] = None):
#         """记录节点结束"""
#         logs = state.get('logs', [])

#         end_log = {
#             'node_name': node_name,
#             'status': 'completed',
#             'timestamp': datetime.now().isoformat(),
#             'output_data': '',  # 将在下面填充
#             'message': f'{node_name}流程完成'
#         }

#         # 提取关键的输出数据
#         if node_name == 'validate_input':
#             end_log['output_data'] = {
#                 'is_clear': state.get('is_clear'),
#                 'clear_check_details': state.get('clear_check_details', {})
#             }
#         elif node_name == 'generate_sql':
#             end_log['output_data'] = {
#                 'sql_query': state.get('sql_query', ''),
#                 'retry_count': state.get('retry_count', 0)
#             }
#         elif node_name == 'execute_sql':
#             result = state.get('execution_result')
#             end_log['output_data'] = {
#                 'row_count': len(result) if result is not None else 0,
#                 'success': result is not None
#             }
#         elif node_name == 'explain_sql':
#             end_log['output_data'] = {
#                 'sql_explanation': state.get('sql_explanation', '')
#             }
#         elif node_name == 'analyze_nl_diff':
#             end_log['output_data'] = {
#                 'nl_diff_analysis': state.get('nl_diff_analysis')
#             }
#         else:
#             end_log['output_data'] = {'status': 'completed'}

#         # 更新进度
#         if progress_callback:
#             # 完成进度比开始进度高一些
#             progress_map = {
#                 'check_training': 20,
#                 'validate_input': 40,
#                 'generate_sql': 60,
#                 'execute_sql': 80,
#                 'explain_sql': 90,
#                 'analyze_nl_diff': 98
#             }
#             progress = progress_map.get(node_name, 60)
#             progress_callback(node_name, f'{node_name}流程完成', progress)

#         self.logger.info(f"节点完成: {node_name}")
#         return end_log


# # 全局进度跟踪器实例
# progress_tracker = ProgressTracker()


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
        if log.get('success') is True:
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
            # 获取进度回调函数
            progress_callback = state.get('progress_callback')

            # 获取现有的日志列表
            logs = state.get('logs', [])

            # 从历史日志计算当前进度
            current_progress = calculate_progress_from_logs(logs)

            # 记录节点开始（进度不变）
            start_log = progress_callback(node_name, f'流程开始', current_progress)

            try:
                # 执行原函数
                result_state = func(state)
                current_step_log = result_state['current_step_log']
                current_step_log['step'] = f"{node_name}: 流程结束"

                # 计算新的进度
                new_progress = current_progress

                # 只有在进度未达到90时才增加
                if current_progress < 90:
                    if current_step_log['success'] == True:
                        # 成功：进度+10，最多到90
                        new_progress = min(current_progress + 10, 90)
                    else:
                        # 失败：进度+5，最多到90
                        new_progress = min(current_progress + 5, 90)

                # 特殊处理最后完成节点
                if node_name == 'analyze_nl_diff' and current_step_log['success'] == True:
                    new_progress = 100

                # 记录节点完成
                if current_step_log['success'] == True:
                    real_status = TaskStatus.RUNNING
                else:
                    real_status = TaskStatus.FAILED

                progress_callback(node_name, f'{node_name}流程结束', new_progress, task_status=real_status,
                                  log_message=current_step_log)
                return result_state

            except Exception as e:
                # 更新进度回调（如果有）
                if progress_callback:
                    progress_callback(node_name, f'{node_name}流程失败', current_progress, TaskStatus.FAILED)

                raise

        return wrapper
    return decorator