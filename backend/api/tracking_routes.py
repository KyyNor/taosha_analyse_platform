"""
操作追踪相关API路由
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime

from services.tracking_service import get_tracking_service
from services.operation_tracking import tracker


# 创建路由器
router = APIRouter(prefix="/tracking", tags=["tracking"])


class SessionSummaryResponse(BaseModel):
    """会话摘要响应"""
    session_id: str
    operation_type: str
    operator: str
    start_time: datetime
    end_time: Optional[datetime]
    total_duration: Optional[int]
    step_count: int
    success_rate: float
    status: str
    error_message: Optional[str]


class StepSummaryResponse(BaseModel):
    """步骤摘要响应"""
    step_sequence: int
    step_name: str
    call_method: str
    success: bool
    duration: int
    error_message: Optional[str]
    has_sql: bool


class FeedbackRequest(BaseModel):
    """用户反馈请求"""
    feedback_type: str  # session_feedback, step_feedback
    session_id: str
    step_sequence: Optional[int] = None
    feedback_sentiment: str  # positive, negative, neutral
    feedback_content: str
    feedback_user: Optional[str] = None


@router.get("/sessions", response_model=List[SessionSummaryResponse])
async def get_recent_sessions(
    limit: int = Query(50, ge=1, le=200),
    operator: Optional[str] = Query(None)
):
    """获取最近的会话列表"""
    tracking_service = get_tracking_service()
    sessions = tracking_service.get_recent_sessions(limit=limit, operator=operator)
    
    return [
        SessionSummaryResponse(
            session_id=session.session_id,
            operation_type=session.operation_type,
            operator=session.operator or "",
            start_time=session.start_time,
            end_time=session.end_time,
            total_duration=session.total_duration,
            step_count=session.step_count,
            success_rate=session.success_rate,
            status=session.status,
            error_message=session.error_message
        )
        for session in sessions
    ]


@router.get("/sessions/{session_id}", response_model=SessionSummaryResponse)
async def get_session_summary(session_id: str):
    """获取指定会话的摘要信息"""
    tracking_service = get_tracking_service()
    session = tracking_service.get_session_summary(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return SessionSummaryResponse(
        session_id=session.session_id,
        operation_type=session.operation_type,
        operator=session.operator or "",
        start_time=session.start_time,
        end_time=session.end_time,
        total_duration=session.total_duration,
        step_count=session.step_count,
        success_rate=session.success_rate,
        status=session.status,
        error_message=session.error_message
    )


@router.get("/sessions/{session_id}/steps", response_model=List[StepSummaryResponse])
async def get_session_steps(session_id: str):
    """获取指定会话的所有步骤"""
    tracking_service = get_tracking_service()
    steps = tracking_service.get_session_steps(session_id)
    
    return [
        StepSummaryResponse(
            step_sequence=step.step_sequence,
            step_name=step.step_name,
            call_method=step.call_method,
            success=step.success,
            duration=step.duration,
            error_message=step.error_message,
            has_sql=step.has_sql
        )
        for step in steps
    ]


@router.get("/sessions/{session_id}/steps/{step_sequence}")
async def get_step_details(session_id: str, step_sequence: int):
    """获取指定步骤的详细信息"""
    tracking_service = get_tracking_service()
    step = tracking_service.get_step_details(session_id, step_sequence)
    
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")
    
    return step


@router.get("/stats")
async def get_operation_stats(days: int = Query(7, ge=1, le=90)):
    """获取操作统计信息"""
    tracking_service = get_tracking_service()
    stats = tracking_service.get_operation_stats(days=days)
    return stats


@router.get("/search")
async def search_sessions(
    query: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100)
):
    """搜索会话"""
    tracking_service = get_tracking_service()
    sessions = tracking_service.search_sessions(query=query, limit=limit)
    
    return [
        SessionSummaryResponse(
            session_id=session.session_id,
            operation_type=session.operation_type,
            operator=session.operator or "",
            start_time=session.start_time,
            end_time=session.end_time,
            total_duration=session.total_duration,
            step_count=session.step_count,
            success_rate=session.success_rate,
            status=session.status,
            error_message=session.error_message
        )
        for session in sessions
    ]


@router.post("/feedback")
async def add_feedback(feedback: FeedbackRequest):
    """添加用户反馈"""
    tracker.add_feedback(
        feedback_type=feedback.feedback_type,
        session_id=feedback.session_id,
        step_sequence=feedback.step_sequence,
        feedback_sentiment=feedback.feedback_sentiment,
        feedback_content=feedback.feedback_content,
        feedback_user=feedback.feedback_user
    )
    
    return {"message": "Feedback added successfully"}


@router.get("/current-session")
async def get_current_session():
    """获取当前活跃的会话ID"""
    session_id = tracker.current_session
    if session_id:
        return {"session_id": session_id, "active": True}
    else:
        return {"session_id": None, "active": False}