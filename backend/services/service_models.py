from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Dict, List, Any, Optional, TypedDict, Union

from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, add_messages
from pydantic import BaseModel

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
class TaskState(BaseModel):
    """统一的任务状态模型 - 兼容LangGraph和API"""
    # 基本信息
    task_id: str
    user_input: str
    operator: Optional[str] = None
    flow_type: str = "fast"
    messages: Optional[List[Union[HumanMessage, AIMessage]]] = None

    # 进度信息
    status: str = "running"  # 'running', 'success', 'failed', 'completed', 'waiting_for_input'
    current_step: str = "初始化"
    progress: int = 0
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # 上下文信息
    task_context: str = ""

    # 业务数据
    sql_query: str = ""
    execution_result: Optional[list[dict]] = None
    clear_check_details: Dict[str, Any] = None
    is_clear: bool = False
    sql_explanation: str = ""
    filtered_vector_ids: Optional[List[str]] = None  # 用于精准过滤检索结果的向量库ID列表

    # 错误和重试
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 5

    # 日志
    logs: List[BaseNodeLog] = None
    current_step_log: Optional[BaseNodeLog] = None
    current_step_name: str = ""
    
    # 人机交互状态
    waiting_for_user_input: bool = False  # 是否等待用户输入
    return_to_node: str = ""  # 用户输入后要返回的节点

    def __post_init__(self):
        """初始化后处理"""
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.logs is None:
            self.logs = []
        if self.clear_check_details is None:
            self.clear_check_details = {}
        if self.messages is None:
            self.messages = []


class TaskStateHelper:
    """TaskState辅助类，提供转换方法"""

    @staticmethod
    def create_default(
        task_id: str,
        user_input: str,
        flow_type: str = 'fast',
        max_retries: Optional[int] = 5,
        operator: Optional[str] = None
    ) -> TaskState:
        """创建默认的TaskState"""
        return TaskState(
            task_id=task_id,
            user_input=user_input,
            operator=operator,
            flow_type=flow_type,
            messages=[],
            status='running',
            current_step='初始化',
            progress=0,
            created_at=datetime.now(),
            task_context='',
            completed_at=None,
            sql_query='',
            execution_result=None,
            clear_check_details={},
            is_clear=False,
            sql_explanation='',
            filtered_vector_ids=None,
            error_message=None,
            retry_count=0,
            max_retries=max_retries,
            logs=[],
            current_step_log=None,
            current_step_name=''
        )

# 注意：GraphState已被移除，统一使用TaskState
# 所有LangGraph工作流现在直接使用TaskState