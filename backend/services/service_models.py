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


# 统一的任务状态模型
@dataclass
class TaskState:
    """统一的任务状态模型"""
    # 基本信息
    task_id: str
    user_input: str
    operator: Optional[str] = None
    flow_type: str = "fast"

    # 进度信息
    status: str = "running"  # 'running', 'success', 'failed'
    current_step: str = "初始化"
    progress: int = 0
    created_at: datetime = None
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
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.logs is None:
            self.logs = []
        if self.clear_check_details is None:
            self.clear_check_details = {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（用于API返回）"""
        import pandas as pd
        from dataclasses import asdict

        data = asdict(self)

        # 转换datetime为ISO格式字符串
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
            elif isinstance(value, pd.DataFrame):
                data[key] = value.to_dict('records') if value is not None else None

        # 添加额外的兼容字段
        if data['execution_result'] is not None:
            data['data'] = data['execution_result']
            # execution_result is now dict array after DataFrame conversion
            data['row_count'] = len(data['execution_result']) if isinstance(data['execution_result'], list) else 0
            data['success'] = True
        else:
            data['data'] = None
            data['row_count'] = 0
            data['success'] = data['status'] in ('success', 'completed')

        return data

    def to_graph_state(self) -> 'GraphState':
        """转换为LangGraph工作流状态"""
        return GraphState(
            user_input=self.user_input,
            task_id=self.task_id,
            flow_type=self.flow_type,
            clear_check_details=self.clear_check_details,
            is_clear=self.is_clear,
            sql_query=self.sql_query,
            execution_result=self.execution_result,
            error_message=self.error_message,
            retry_count=self.retry_count,
            max_retries=self.max_retries,
            logs=self.logs,
            current_step_log=self.current_step_log,
            current_step_name=self.current_step_name,
            current_progress=self.current_progress
        )

    @classmethod
    def from_graph_state(cls, state: 'GraphState') -> 'TaskState':
        """从LangGraph状态创建TaskState"""
        return cls(
            task_id=state['task_id'],
            user_input=state['user_input'],
            flow_type=state.get('flow_type', 'fast'),
            sql_query=state.get('sql_query', ''),
            execution_result=state.get('execution_result'),
            clear_check_details=state.get('clear_check_details', {}),
            is_clear=state.get('is_clear', False),
            error_message=state.get('error_message'),
            retry_count=state.get('retry_count', 0),
            max_retries=state.get('max_retries', 5),
            logs=state.get('logs', []),
            current_step_log=state.get('current_step_log'),
            current_step_name=state.get('current_step_name', ''),
            current_progress=state.get('current_progress', 0)
        )


# LangGraph工作流状态定义（保持向后兼容）
class GraphState(TypedDict):
    """LangGraph状态定义"""
    user_input: str
    task_id: str
    flow_type: str  # 新增：流程类型 ("fast" 或 "thorough")
    clear_check_details: Dict[str, Any]
    is_clear: bool
    sql_query: str
    execution_result: Optional[pd.DataFrame]
    error_message: Optional[str]
    retry_count: int
    max_retries: int
    logs: List[BaseNodeLog]
    current_step_log: BaseNodeLog | None
    current_step_name: str
    current_progress: int