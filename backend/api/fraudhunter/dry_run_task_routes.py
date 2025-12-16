"""
FraudHunter任务管理API路由
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from urllib.parse import quote
import io
import pandas as pd
from models.db_base import get_db
from schemas.fraudhunter.task import (
    TaskProgressResponse,
    TaskResultResponse,
    TaskExecutionListResponse,
    TaskExecutionItem,
)
from services.fraudhunter.dry_run_task_service import dry_run_task_manager
from utils.logger import logger
from utils.excel_exporter import create_excel_exporter


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


@router.get("/{task_id}/export/excel", summary="导出任务结果为Excel")
async def export_task_result_excel(
    task_id: str,
    db: Session = Depends(get_db)
):
    """导出任务执行结果为Excel文件

    参数:
    - task_id: 任务执行ID

    返回:
    - Excel文件流，可直接下载
    """
    try:
        # 获取任务结果
        task_result = dry_run_task_manager.get_task_result(db, task_id)

        if task_result['status'] != 'success':
            raise HTTPException(status_code=400, detail="只有成功的任务才能导出结果")

        result_data = task_result.get('result', {})

        # 提取matched_records数据
        matched_records = result_data.get('matched_records', [])

        if not matched_records:
            raise HTTPException(status_code=400, detail="没有可导出的命中记录")

        # 准备数据表
        data_sheets = {}

        # 1. 命中记录表
        data_sheets['命中记录'] = pd.DataFrame(matched_records)

        # 2. 执行统计表
        stats_data = {
            '指标': ['总天数', '成功天数', '跳过天数', '失败天数', '总命中记录数'],
            '数值': [
                result_data.get('total_days', 0),
                result_data.get('success_days', 0),
                result_data.get('skipped_days', 0),
                result_data.get('failed_days', 0),
                result_data.get('total_rows_matched', 0)
            ]
        }
        data_sheets['执行统计'] = pd.DataFrame(stats_data)

        # 3. 每日执行详情表（如果有）
        daily_results = result_data.get('daily_results', [])
        if daily_results:
            data_sheets['每日执行详情'] = pd.DataFrame(daily_results)

        # 使用Excel导出器生成文件
        exporter = create_excel_exporter()
        output = exporter.export_to_bytes(data_sheets)

        # 准备文件响应
        filename = f"backtest_{task_id}.xlsx"
        # 使用RFC 5987格式支持Unicode文件名
        encoded_filename = quote(filename)

        return StreamingResponse(
            io.BytesIO(output.read()),
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={
                "Content-Disposition": f"attachment; filename={filename}; filename*=UTF-8''{encoded_filename}"
            }
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"导出Excel失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"导出Excel失败: {str(e)}")
