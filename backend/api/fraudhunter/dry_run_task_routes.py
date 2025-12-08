"""
FraudHunter任务管理API路由
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from models.db_base import get_db
from schemas.fraudhunter.task import (
    TaskProgressResponse,
    TaskResultResponse,
    TaskExecutionListResponse,
    TaskExecutionItem,
)
from services.fraudhunter.dry_run_task_service import dry_run_task_manager
from utils.logger import logger


router = APIRouter(prefix="/tasks", tags=["任务管理"])


@router.get("/{task_id}/progress", response_model=TaskProgressResponse, summary="查询任务进度")
async def get_task_progress(
    task_id: str,
    db: Session = Depends(get_db)
):
    """查询任务执行进度

    参数:
    - task_id: 任务执行ID

    返回:
    - status: 任务状态（pending/running/success/failed/cancelled）
    - progress: 进度百分比
    - current_step: 当前步骤
    - estimated_remaining_seconds: 预计剩余时间（秒）
    """
    try:
        progress = dry_run_task_manager.get_task_progress(db, task_id)
        return progress

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"查询任务进度失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询任务进度失败: {str(e)}")


@router.get("/{task_id}/result", response_model=TaskResultResponse, summary="获取任务结果")
async def get_task_result(
    task_id: str,
    db: Session = Depends(get_db)
):
    """获取任务执行结果

    只有状态为success或failed的任务才能获取结果

    参数:
    - task_id: 任务执行ID

    返回:
    - status: 任务状态
    - duration_seconds: 执行时长
    - result: 执行结果数据
    """
    try:
        result = dry_run_task_manager.get_task_result(db, task_id)
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"获取任务结果失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取任务结果失败: {str(e)}")


@router.post("/{task_id}/cancel", summary="取消任务")
async def cancel_task(
    task_id: str,
    db: Session = Depends(get_db)
):
    """取消正在执行的任务

    参数:
    - task_id: 任务执行ID

    返回:
    - success: 是否成功取消
    """
    try:
        success = await dry_run_task_manager.cancel_task(db, task_id)

        if success:
            return {'message': f'任务 {task_id} 已取消', 'success': True}
        else:
            return {'message': f'任务 {task_id} 无法取消（可能已完成或不存在）', 'success': False}

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"取消任务失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"取消任务失败: {str(e)}")


@router.get("/executions", response_model=TaskExecutionListResponse, summary="查询任务执行历史")
async def list_task_executions(
    task_type: Optional[str] = Query(None, description="任务类型筛选（indicator/model）"),
    task_id: Optional[int] = Query(None, description="任务ID筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db)
):
    """查询任务执行历史

    支持按任务类型和任务ID筛选

    参数:
    - task_type: 任务类型（indicator/model）
    - task_id: 任务ID（指标组ID或模型ID）
    - page: 页码
    - page_size: 每页数量

    返回:
    - total: 总数
    - items: 任务执行记录列表
    """
    try:
        items, total = dry_run_task_manager.list_task_executions(
            db=db,
            task_type=task_type,
            task_id=task_id,
            page=page,
            page_size=page_size
        )

        return {
            'total': total,
            'page': page,
            'page_size': page_size,
            'items': items
        }

    except Exception as e:
        logger.error(f"查询任务执行历史失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询任务执行历史失败: {str(e)}")
