"""
DeepAgents API 路由

提供数据分析任务的 REST API 接口：
- 提交分析任务
- 查询会话列表和详情
- 下载分析结果
- 获取队列状态
"""

import io
import uuid
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc

from models.db_base import get_db
from models.deepagents.analysis_tracking_models import AnalysisSession, AnalysisScore
from services.deepagents import get_task_executor
from utils.logger import logger


router = APIRouter(prefix="/deepagents", tags=["DeepAgents数据分析"])


# ============ 请求/响应模型 ============

class SubmitTaskRequest(BaseModel):
    """提交分析任务请求"""
    question: str = Field(..., min_length=1, max_length=2000, description="分析问题")
    question_source: str = Field("api", description="问题来源: api/manual/proposer")


class SubmitTaskResponse(BaseModel):
    """提交任务响应"""
    session_id: str
    status: str
    message: str


class SessionListItem(BaseModel):
    """会话列表项"""
    id: int
    session_id: str
    question: str
    question_source: Optional[str]
    status: str
    start_time: Optional[str]
    end_time: Optional[str]
    duration_seconds: Optional[float]
    overall_score: Optional[int]
    created_at: str


class SessionListResponse(BaseModel):
    """会话列表响应"""
    items: List[SessionListItem]
    total: int
    page: int
    page_size: int


class SessionDetailResponse(BaseModel):
    """会话详情响应"""
    session: dict
    scores: Optional[dict]


class QueueStatusResponse(BaseModel):
    """队列状态响应"""
    is_running: bool
    queue_size: int
    running_count: int
    current_task: Optional[dict]


# ============ API 端点 ============

@router.post("/submit", response_model=SubmitTaskResponse, summary="提交分析任务")
async def submit_analysis_task(
    request: SubmitTaskRequest,
    db: Session = Depends(get_db)
):
    """
    提交新的数据分析任务到后台队列

    - 任务将在后台异步执行
    - 同一时间只会执行一个任务（使用数据库锁保证）
    - 每个任务最多执行20分钟，超时将被强制终止
    """
    try:
        # 生成会话ID
        session_id = str(uuid.uuid4())

        # 创建会话记录
        session = AnalysisSession(
            session_id=session_id,
            question=request.question,
            question_source=request.question_source,
            status="pending",
            created_at=datetime.now()
        )
        db.add(session)
        db.commit()

        logger.info(f"分析任务已提交: {session_id}")

        return SubmitTaskResponse(
            session_id=session_id,
            status="pending",
            message="任务已提交到队列，等待执行"
        )

    except Exception as e:
        logger.error(f"提交任务失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"提交任务失败: {str(e)}")


@router.get("/sessions", response_model=SessionListResponse, summary="获取分析会话列表")
async def list_sessions(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(None, description="状态筛选: pending/running/completed/failed"),
    search: Optional[str] = Query(None, description="搜索问题关键词"),
    db: Session = Depends(get_db)
):
    """
    获取分析会话列表，支持分页和筛选

    返回字段包括:
    - 基本信息: ID、问题、来源、状态
    - 时间信息: 开始时间、结束时间、耗时
    - 评分信息: 综合评分
    """
    try:
        # 构建查询
        query = db.query(AnalysisSession)

        if status:
            query = query.filter(AnalysisSession.status == status)

        if search:
            query = query.filter(AnalysisSession.question.like(f"%{search}%"))

        # 获取总数
        total = query.count()

        # 分页查询
        offset = (page - 1) * page_size
        sessions = query.order_by(
            desc(AnalysisSession.created_at)
        ).offset(offset).limit(page_size).all()

        # 构建响应
        items = []
        for session in sessions:
            # 获取评分
            score = db.query(AnalysisScore).filter(
                AnalysisScore.session_id == session.session_id
            ).first()

            # 截断问题文本
            question_text = session.question
            if len(question_text) > 100:
                question_text = question_text[:100] + "..."

            items.append(SessionListItem(
                id=session.id,
                session_id=session.session_id,
                question=question_text,
                question_source=session.question_source,
                status=session.status,
                start_time=session.start_time.isoformat() if session.start_time else None,
                end_time=session.end_time.isoformat() if session.end_time else None,
                duration_seconds=session.duration_seconds,
                overall_score=score.overall_score if score else None,
                created_at=session.created_at.isoformat() if session.created_at else ""
            ))

        return SessionListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size
        )

    except Exception as e:
        logger.error(f"获取会话列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取会话列表失败: {str(e)}")


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse, summary="获取会话详情")
async def get_session_detail(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    获取指定会话的详细信息

    包括:
    - 会话基本信息
    - LLM输出内容
    - 报告路径
    - 各项评分和理由
    """
    try:
        # 查询会话
        session = db.query(AnalysisSession).filter(
            AnalysisSession.session_id == session_id
        ).first()

        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")

        # 查询评分
        score = db.query(AnalysisScore).filter(
            AnalysisScore.session_id == session_id
        ).first()

        return SessionDetailResponse(
            session=session.to_dict(),
            scores=score.to_dict() if score else None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取会话详情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取会话详情失败: {str(e)}")


@router.get("/sessions/{session_id}/download", summary="下载分析结果")
async def download_session_output(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    下载指定会话的分析结果目录（打包为zip）

    包含:
    - 报告HTML文件
    - 生成的图表图片
    - 中间数据文件
    """
    try:
        # 查询会话
        session = db.query(AnalysisSession).filter(
            AnalysisSession.session_id == session_id
        ).first()

        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")

        if not session.report_path:
            raise HTTPException(status_code=404, detail="该会话没有生成报告")

        # 获取输出目录
        report_path = Path(session.report_path)
        output_dir = report_path.parent

        if not output_dir.exists():
            raise HTTPException(status_code=404, detail="输出目录不存在")

        # 创建 zip 文件
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for file_path in output_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(output_dir)
                    zip_file.write(file_path, arcname)

        zip_buffer.seek(0)

        # 生成文件名
        filename = f"analysis_{session_id[:8]}.zip"

        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"下载失败: {str(e)}")


@router.get("/queue/status", response_model=QueueStatusResponse, summary="获取队列状态")
async def get_queue_status():
    """获取当前任务队列状态"""
    try:
        executor = get_task_executor()
        status = executor.get_queue_status()
        return QueueStatusResponse(**status)
    except Exception as e:
        logger.error(f"获取队列状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取队列状态失败: {str(e)}")


@router.post("/queue/start", summary="启动任务队列")
async def start_queue():
    """启动任务队列处理器（仅用于手动控制）"""
    try:
        executor = get_task_executor()
        executor.start()
        return {"status": "success", "message": "任务队列已启动"}
    except Exception as e:
        logger.error(f"启动队列失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"启动队列失败: {str(e)}")


@router.post("/queue/stop", summary="停止任务队列")
async def stop_queue():
    """停止任务队列处理器（仅用于手动控制）"""
    try:
        executor = get_task_executor()
        executor.stop()
        return {"status": "success", "message": "任务队列已停止"}
    except Exception as e:
        logger.error(f"停止队列失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"停止队列失败: {str(e)}")
