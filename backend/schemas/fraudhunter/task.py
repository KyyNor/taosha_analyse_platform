"""
FraudHunter任务相关Pydantic schemas
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from datetime import datetime


class TaskProgressResponse(BaseModel):
    """任务进度响应模型"""
    task_id: str = Field(..., description="任务ID")
    task_type: str = Field(..., description="任务类型")
    parent_execution_id: Optional[str] = Field(None, description="父任务执行ID")
    status: str = Field(..., description="任务状态：pending/running/success/failed/cancelled")
    progress: Optional[float] = Field(None, description="进度百分比（0-100）")
    current_step: Optional[str] = Field(None, description="当前步骤")
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    estimated_remaining_seconds: Optional[int] = Field(None, description="预计剩余时间（秒）")

    class Config:
        from_attributes = True


class TaskResultResponse(BaseModel):
    """任务结果响应模型"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
    duration_seconds: Optional[int] = Field(None, description="执行时长（秒）")
    result: Optional[Dict[str, Any]] = Field(None, description="执行结果")

    class Config:
        from_attributes = True


class TaskExecutionItem(BaseModel):
    """任务执行记录项"""
    id: int
    task_type: str
    task_id: int
    execution_id: str
    parent_execution_id: Optional[str] = None
    status: str
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    created_by: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class TaskExecutionListResponse(BaseModel):
    """任务执行历史列表响应"""
    total: int
    page: int
    page_size: int
    items: List[TaskExecutionItem]
