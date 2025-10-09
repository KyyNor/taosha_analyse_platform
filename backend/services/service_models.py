from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Any, Optional, Union

import pandas as pd
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


# 统一的任务状态模型 - 兼容LangGraph和API（使用dataclass）
@dataclass
class TaskState:
    """统一的任务状态模型 - 兼容LangGraph和API"""
    # 基本信息
    task_id: str
    user_input: str
    operator: Optional[str] = None
    flow_type: str = "fast"

    # 进度信息
    status: str = "running"  # 'running', 'success', 'failed', 'completed'
    current_step: str = "初始化"
    progress: int = 0
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # 业务数据
    sql_query: str = ""
    execution_result: Optional[pd.DataFrame] = None
    clear_check_details: Dict[str, Any] = None
    is_clear: bool = False

    # 错误和重试
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 5

    # 日志
    logs: List[BaseNodeLog] = None
    current_step_log: Optional[BaseNodeLog] = None
    current_step_name: str = ""
    current_progress: int = 0

    def __post_init__(self):
        """初始化后处理"""
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.started_at is None:
            self.started_at = datetime.now()
        if self.logs is None:
            self.logs = []
        if self.clear_check_details is None:
            self.clear_check_details = {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（用于API返回）"""
        return TaskStateHelper.to_dict(self)


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
            current_step='初始化',
            progress=0,
            created_at=datetime.now(),
            started_at=datetime.now(),
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
    def to_dict(state: 'TaskState') -> Dict[str, Any]:
        """转换为字典格式（用于API返回）"""
        import pandas as pd
        from dataclasses import asdict

        data = asdict(state)

        # 转换datetime为ISO格式字符串
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()

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
            data['success'] = False

        return data

    @staticmethod
    def update_status(state: TaskState, status: str, error_message: Optional[str] = None) -> TaskState:
        """更新状态"""
        state.status = status
        if error_message:
            state.error_message = error_message
        if status in ('success', 'failed', 'completed'):
            state.completed_at = datetime.now()
        return state

    @staticmethod
    def update_progress(state: TaskState, current_step: str, progress: int) -> TaskState:
        """更新进度"""
        state.current_step = current_step
        state.current_progress = progress
        state.progress = progress
        state.current_step_name = current_step
        return state

    @staticmethod
    def add_log(state: TaskState, log: BaseNodeLog) -> TaskState:
        """添加日志"""
        if state.logs is None:
            state.logs = []
        state.logs.append(log)
        state.current_step_log = log
        return state


# 注意：GraphState已被移除，统一使用TaskState
# 所有LangGraph工作流现在直接使用TaskState