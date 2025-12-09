"""
FraudHunter宽表版本管理API路由
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, date
from typing import List
from models.db_base import get_db
from schemas.fraudhunter.wide_table import (
    IndicatorRunProgressCallback,
    IndicatorRunProgressResponse,
    WideTableVersionInfo,
    WideTableSnapshotInfo
)
from models.fraudhunter.wide_table import (
    FraudHunterIndicatorRunProgress,
    FraudHunterWideTableVersion,
    FraudHunterWideTableSnapshot
)
from models.fraudhunter.indicator import FraudHunterIndicatorTask
from utils.logger import logger


router = APIRouter(prefix="/wide-table", tags=["宽表版本管理"])


@router.post(
    "/indicator-runs/callback",
    response_model=IndicatorRunProgressResponse,
    summary="指标运行进度回调"
)
async def indicator_run_progress_callback(
    callback_data: IndicatorRunProgressCallback,
    db: Session = Depends(get_db)
):
    """DS任务执行完成后回调此API更新运行进度

    Args:
        callback_data: 回调数据（仅需3个字段：indicator_task_id, indicator_version, etl_date）

    Returns:
        更新结果
    """
    try:
        # 1. 验证指标任务是否存在
        indicator_task = db.query(FraudHunterIndicatorTask).filter(
            FraudHunterIndicatorTask.id == callback_data.indicator_task_id
        ).first()

        if not indicator_task:
            raise HTTPException(
                status_code=404,
                detail=f"指标任务不存在: {callback_data.indicator_task_id}"
            )

        # 2. 解析ETL日期
        etl_date = datetime.strptime(callback_data.etl_date, '%Y-%m-%d').date()

        # 3. 查找或创建进度记录
        progress = db.query(FraudHunterIndicatorRunProgress).filter(
            FraudHunterIndicatorRunProgress.indicator_task_id == callback_data.indicator_task_id,
            FraudHunterIndicatorRunProgress.etl_date == etl_date,
            FraudHunterIndicatorRunProgress.indicator_version == callback_data.indicator_version
        ).first()

        if progress:
            # 更新现有记录
            progress.finish_time = datetime.utcnow()
            logger.info(
                f"更新指标运行进度: "
                f"task_id={callback_data.indicator_task_id}, "
                f"etl_date={etl_date}, "
                f"version={callback_data.indicator_version}"
            )
        else:
            # 创建新记录
            progress = FraudHunterIndicatorRunProgress(
                indicator_task_id=callback_data.indicator_task_id,
                indicator_version=callback_data.indicator_version,
                etl_date=etl_date,
                finish_time=datetime.utcnow()
            )
            db.add(progress)
            logger.info(
                f"创建指标运行进度记录: "
                f"task_id={callback_data.indicator_task_id}, "
                f"etl_date={etl_date}"
            )

        db.commit()
        db.refresh(progress)

        # 4. 记录完成（同步由定时任务处理，不在此触发）
        logger.info(
            f"指标运行进度已更新: "
            f"task_id={callback_data.indicator_task_id}, "
            f"etl_date={etl_date}, "
            f"version={callback_data.indicator_version}"
        )

        return IndicatorRunProgressResponse(
            success=True,
            message="运行进度已更新",
            progress_id=progress.id,
            version_sync_triggered=False  # 不再通过回调触发同步
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"指标运行进度回调失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"回调失败: {str(e)}")


@router.get(
    "/versions",
    response_model=List[WideTableVersionInfo],
    summary="查询版本列表"
)
async def list_versions(
    wide_table_name: str = None,
    status: str = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """查询宽表版本列表

    Args:
        wide_table_name: 宽表名称过滤（可选）
        status: 状态过滤（current/target/history/skipped）（可选）
        skip: 跳过记录数
        limit: 返回记录数

    Returns:
        版本列表
    """
    query = db.query(FraudHunterWideTableVersion)

    if wide_table_name:
        query = query.filter(FraudHunterWideTableVersion.wide_table_name == wide_table_name)

    if status:
        query = query.filter(FraudHunterWideTableVersion.status == status)

    versions = query.order_by(
        FraudHunterWideTableVersion.created_at.desc()
    ).offset(skip).limit(limit).all()

    return versions


@router.get(
    "/versions/{version_hash}",
    response_model=WideTableVersionInfo,
    summary="查询版本详情"
)
async def get_version(
    version_hash: str,
    db: Session = Depends(get_db)
):
    """查询指定版本的详细信息

    Args:
        version_hash: 版本号

    Returns:
        版本详情
    """
    version = db.query(FraudHunterWideTableVersion).filter(
        FraudHunterWideTableVersion.version_hash == version_hash
    ).first()

    if not version:
        raise HTTPException(status_code=404, detail=f"版本不存在: {version_hash}")

    return version


@router.get(
    "/snapshots",
    response_model=List[WideTableSnapshotInfo],
    summary="查询快照列表"
)
async def list_snapshots(
    wide_table_name: str = None,
    etl_date: str = None,
    status: str = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """查询宽表快照列表

    Args:
        wide_table_name: 宽表名称过滤（可选）
        etl_date: ETL日期过滤（YYYY-MM-DD格式）（可选）
        status: 状态过滤（generating/ready/failed）（可选）
        skip: 跳过记录数
        limit: 返回记录数

    Returns:
        快照列表
    """
    query = db.query(FraudHunterWideTableSnapshot)

    if wide_table_name:
        query = query.filter(FraudHunterWideTableSnapshot.wide_table_name == wide_table_name)

    if etl_date:
        try:
            etl_date_obj = datetime.strptime(etl_date, '%Y-%m-%d').date()
            query = query.filter(FraudHunterWideTableSnapshot.etl_date == etl_date_obj)
        except ValueError:
            raise HTTPException(status_code=400, detail="etl_date格式必须是YYYY-MM-DD")

    if status:
        query = query.filter(FraudHunterWideTableSnapshot.status == status)

    snapshots = query.order_by(
        FraudHunterWideTableSnapshot.created_at.desc()
    ).offset(skip).limit(limit).all()

    return snapshots