from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Any, Optional, Union

import pandas as pd
from typing_extensions import TypedDict
from utils.logger import logger


@dataclass
class BaseNodeLog:
    """日志记录结构"""
    step: str
    input_data: str
    prompt: str
    model_output: str
    success: bool
    error: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


# 统一的任务状态模型 - 兼容LangGraph和API（使用TypedDict）
class TaskState(TypedDict):
    """统一的任务状态模型 - 兼容LangGraph TypedDict"""
    # 基本信息
    task_id: str
    user_input: str
    operator: Optional[str]
    flow_type: str

    # 进度信息
    status: str  # 'running', 'success', 'failed'
    current_step: str
    progress: int
    created_at: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]

    # 业务数据
    sql_query: str
    execution_result: Optional[pd.DataFrame]
    clear_check_details: Dict[str, Any]
    is_clear: bool

    # 错误和重试
    error_message: Optional[str]
    retry_count: int
    max_retries: int

    # 日志
    logs: List[BaseNodeLog]
    current_step_log: Optional[BaseNodeLog]
    current_step_name: str
    current_progress: int


class TaskStateHelper:
    """TaskState辅助类，提供转换方法"""

    @staticmethod
    def create_default(
        task_id: str,
        user_input: str,
        flow_type: str = 'fast',
        operator: Optional[str] = None
    ) -> TaskState:
        """创建默认的TaskState"""
        return TaskState(
            task_id=task_id,
            user_input=user_input,
            operator=operator,
            flow_type=flow_type,
            status='running',
            current_step='',
            progress=0,
            created_at=datetime.now().isoformat(),
            started_at=datetime.now().isoformat(),
            completed_at=None,
            sql_query='',
            execution_result=None,
            clear_check_details={},
            is_clear=False,
            error_message=None,
            retry_count=0,
            max_retries=5,
            logs=[],
            current_step_log=None,
            current_step_name='',
            current_progress=0
        )

    @staticmethod
    def to_dict(state: TaskState) -> Dict[str, Any]:
        """转换为字典格式（用于API返回）"""
        data = dict(state)

        # 转换DataFrame为字典数组
        if data['execution_result'] is not None:
            df = data['execution_result']
            if isinstance(df, pd.DataFrame):
                # 转换为字典数组，并包含列信息
                records = df.to_dict('records')
                data['execution_result'] = records
                data['data'] = records

                # 添加列信息
                data['columns'] = [
                    {"name": col, "type": str(df[col].dtype)}
                    for col in df.columns
                ]
                data['row_count'] = len(records)
                data['success'] = True
            else:
                # 如果已经是其他格式，保持原样
                data['data'] = data['execution_result']
                data['row_count'] = len(data['execution_result']) if isinstance(data['execution_result'], list) else 0
                data['success'] = True
        else:
            data['data'] = None
            data['row_count'] = 0
            data['success'] = data['status'] in ('success', 'completed')

        return data

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> TaskState:
        """从字典创建TaskState"""
        # 处理execution_result - 如果是字典数组，转换为DataFrame
        if 'execution_result' in data and data['execution_result'] is not None:
            execution_result = data['execution_result']
            if isinstance(execution_result, list) and execution_result:
                # 检查是否是字典数组
                if isinstance(execution_result[0], dict):
                    try:
                        # 转换为DataFrame
                        df = pd.DataFrame(execution_result)
                        data['execution_result'] = df
                    except Exception as e:
                        logger.warning(f"Failed to convert execution_result to DataFrame: {e}")
                        # 保持原格式
                        pass

        # 处理logs
        if 'logs' in data and data['logs'] is not None:
            logs = data['logs']
            if isinstance(logs, list):
                # 确保每个log都是BaseNodeLog格式
                formatted_logs = []
                for log in logs:
                    if isinstance(log, dict):
                        # 转换为BaseNodeLog
                        formatted_log = BaseNodeLog(
                            step=log.get('step', ''),
                            input_data=log.get('input_data', ''),
                            prompt=log.get('prompt', ''),
                            model_output=log.get('model_output', ''),
                            success=log.get('success', True),
                            error=log.get('error'),
                            start_time=pd.to_datetime(log['start_time']) if log.get('start_time') else None,
                            end_time=pd.to_datetime(log['end_time']) if log.get('end_time') else None
                        )
                        formatted_logs.append(formatted_log)
                    else:
                        formatted_logs.append(log)
                data['logs'] = formatted_logs

        return TaskState(data)

    @staticmethod
    def update_status(state: TaskState, status: str, error_message: Optional[str] = None) -> TaskState:
        """更新状态"""
        state['status'] = status
        if error_message:
            state['error_message'] = error_message
        if status in ('success', 'failed', 'completed'):
            state['completed_at'] = datetime.now().isoformat()
        return state

    @staticmethod
    def update_progress(state: TaskState, current_step: str, progress: int) -> TaskState:
        """更新进度"""
        state['current_step'] = current_step
        state['current_progress'] = progress
        state['progress'] = progress
        return state

    @staticmethod
    def add_log(state: TaskState, log: BaseNodeLog) -> TaskState:
        """添加日志"""
        if state['logs'] is None:
            state['logs'] = []
        state['logs'].append(log)
        state['current_step_log'] = log
        return state


# 注意：GraphState已被移除，统一使用TaskState
# 所有LangGraph工作流现在直接使用TaskState