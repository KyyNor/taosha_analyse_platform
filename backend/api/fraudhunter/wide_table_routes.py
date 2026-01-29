"""
FraudHunter宽表版本管理API路由
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, distinct
from datetime import datetime, timedelta
from typing import List, Optional
from services.fraudhunter.wide_table_service.version_manager import WideTableVersionManager
from models.db_base import get_db
from utils.config import settings
from schemas.fraudhunter.wide_table import (
    IndicatorRunProgressCallback,
    IndicatorRunProgressResponse,
    WideTableVersionInfo,
    WideTableSnapshotInfo,
    WideTableVersionDetailInfo,
    WideTableVersionProgressInfo,
    WideTableVersionListResponse,
    IndicatorProgressInfo,
    IncompleteTaskInfo,
    DateProgressDetail
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
            progress.finish_time = datetime.now()
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
                finish_time=datetime.now()
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
    response_model=WideTableVersionListResponse,
    summary="查询版本列表（分页）"
)
async def list_versions(
    wide_table_name: Optional[str] = Query(None, description="宽表名称过滤"),
    status: Optional[str] = Query(None, description="状态过滤（current/target/history/skipped）"),
    search: Optional[str] = Query(None, description="搜索（模糊匹配版本哈希）"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db)
):
    """查询宽表版本列表

    Args:
        wide_table_name: 宽表名称过滤（可选）
        status: 状态过滤（current/target/history/skipped）（可选）
        search: 搜索（模糊匹配版本哈希）（可选）
        page: 页码（从1开始）
        page_size: 每页数量

    Returns:
        分页版本列表
    """
    query = db.query(FraudHunterWideTableVersion)

    if wide_table_name:
        query = query.filter(FraudHunterWideTableVersion.wide_table_name == wide_table_name)

    if status:
        query = query.filter(FraudHunterWideTableVersion.status == status)

    # 新增：搜索版本哈希
    if search:
        query = query.filter(FraudHunterWideTableVersion.version_hash.like(f"%{search}%"))

    # 计算总数
    total = query.count()

    # 分页查询
    skip = (page - 1) * page_size
    versions = query.order_by(
        FraudHunterWideTableVersion.created_at.desc()
    ).offset(skip).limit(page_size).all()

    return WideTableVersionListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=versions
    )


@router.get(
    "/versions/{version_hash}",
    response_model=WideTableVersionDetailInfo,
    summary="查询版本详情（含指标清单和执行进度）"
)
async def get_version(
    version_hash: str,
    db: Session = Depends(get_db)
):
    """查询指定版本的详细信息，包含：
    - 版本基本信息
    - 参与指标清单（从indicator_metadata解析）
    - 已完成执行的ETL日期列表

    Args:
        version_hash: 版本号

    Returns:
        版本详情（含指标和进度）
    """
    lookback_days = settings.fraudhunter_wide_table_sync_lookback_days

    version = db.query(FraudHunterWideTableVersion).filter(
        FraudHunterWideTableVersion.version_hash == version_hash
    ).first()

    if not version:
        raise HTTPException(status_code=404, detail=f"版本不存在: {version_hash}")

    # 解析indicator_metadata，构建指标清单
    indicators = []
    indicator_metadata = version.indicator_metadata or {}

    indicator_dict = {}

    for indicator_id_str, meta in indicator_metadata.items():
        indicators.append(IndicatorProgressInfo(
            indicator_id=int(indicator_id_str),
            indicator_code=meta.get('indicator_code', ''),
            indicator_name=meta.get('indicator_name', ''),
            indicator_type=meta.get('indicator_type', 'offline'),
            indicator_version=meta.get('version', 1),
            indicator_task_id=meta.get('indicator_task_id')
        ))
        indicator_dict[str(meta.get('indicator_task_id'))] = str(meta.get('version', 1))

    # 查询快照数量
    snapshot_count = db.query(func.count(FraudHunterWideTableSnapshot.id)).filter(
        FraudHunterWideTableSnapshot.version_hash == version_hash,
        FraudHunterWideTableSnapshot.status == 'ready'
    ).scalar() or 0

    # 查询已完成执行的ETL日期列表
    # 根据indicator_metadata中的indicator_task_id找到所有相关的运行进度
    completed_dates = []

    now_date = datetime.now().date()
    start_date_str = (now_date - timedelta(days=lookback_days)).strftime("%Y-%m-%d")

    all_run_progress = db.query(
        FraudHunterIndicatorRunProgress.etl_date, 
        FraudHunterIndicatorRunProgress.indicator_task_id, 
        func.max(FraudHunterIndicatorRunProgress.indicator_version).label('indicator_version')
    ).filter(
        and_(
                FraudHunterIndicatorRunProgress.etl_date >= start_date_str,
            )
    ).group_by(
        FraudHunterIndicatorRunProgress.etl_date, 
        FraudHunterIndicatorRunProgress.indicator_task_id
    ).all()

    for i in range(lookback_days, 0, -1):  # 倒序，从 version_manager 到 1
        date_obj = now_date - timedelta(days=i)
        formatted_date = date_obj.strftime("%Y-%m-%d")
        is_completed = True
        for _indicator_task_id, _indicator_version in indicator_dict.items():
            r = list(filter(lambda p: p[0] == date_obj and str(p[1]) == _indicator_task_id and str(p[2]) == _indicator_version, all_run_progress))
            if not r:
                is_completed = False
        if is_completed:
            completed_dates.append(formatted_date)

    completed_dates.sort(reverse=True)

    return WideTableVersionDetailInfo(
        id=version.id,
        wide_table_name=version.wide_table_name,
        version_hash=version.version_hash,
        indicator_metadata=version.indicator_metadata,
        status=version.status,
        target_at=version.target_at,
        current_at=version.current_at,
        history_at=version.history_at,
        skipped_at=version.skipped_at,
        created_by=version.created_by,
        created_at=version.created_at,
        updated_at=version.updated_at,
        indicators=indicators,
        snapshot_count=snapshot_count,
        completed_dates=completed_dates
    )


@router.get(
    "/versions/{version_hash}/progress",
    response_model=WideTableVersionProgressInfo,
    summary="查询版本执行进度（含未完成任务详情）"
)
async def get_version_progress(
    version_hash: str,
    db: Session = Depends(get_db)
):
    """查询指定版本的执行进度详情（含未完成任务列表）

    自动使用配置项 fraudhunter_wide_table_sync_lookback_days 决定查询周期

    Args:
        version_hash: 版本号
        db: 数据库会话

    Returns:
        增强版执行进度信息（包含未完成任务详情）
    """
    version = db.query(FraudHunterWideTableVersion).filter(
        FraudHunterWideTableVersion.version_hash == version_hash
    ).first()

    if not version:
        raise HTTPException(status_code=404, detail=f"版本不存在: {version_hash}")

    # 从配置读取查询周期（默认30天）
    lookback_days = settings.fraudhunter_wide_table_sync_lookback_days

    indicator_metadata = version.indicator_metadata or {}

    # 获取所有关联的indicator_task_id（去重）
    task_ids = list(set([
        meta.get('indicator_task_id')
        for meta in indicator_metadata.values()
        if meta.get('indicator_task_id')
    ]))

    completed_dates = []
    recent_progress = []

    tasks_map = {
        task.id: task
        for task in db.query(FraudHunterIndicatorTask).filter(
            FraudHunterIndicatorTask.id.in_(task_ids)
        ).all()
    }

    indicator_dict = {}

    for indicator_id_str, meta in indicator_metadata.items():
        indicator_dict[str(meta.get('indicator_task_id'))] = str(meta.get('version', 1))


    now_date = datetime.now().date()
    start_date_str = (now_date - timedelta(days=lookback_days)).strftime("%Y-%m-%d")

    all_run_progress = db.query(
        FraudHunterIndicatorRunProgress.etl_date, 
        FraudHunterIndicatorRunProgress.indicator_task_id, 
        func.max(FraudHunterIndicatorRunProgress.indicator_version).label('indicator_version'),
        func.max(FraudHunterIndicatorRunProgress.finish_time).label('finish_time')
    ).filter(
        and_(
                FraudHunterIndicatorRunProgress.etl_date >= start_date_str,
            )
    ).group_by(
        FraudHunterIndicatorRunProgress.etl_date, 
        FraudHunterIndicatorRunProgress.indicator_task_id
    ).all()

    total_count = len(indicator_dict)

    for i in range(1, lookback_days + 1):  # 倒序，从 version_manager 到 1
        date_obj = now_date - timedelta(days=i)
        formatted_date = date_obj.strftime("%Y-%m-%d")
        is_completed = True
        incomplete_task_ids = set()
        last_finish_time = None

        for _indicator_task_id, _indicator_version in indicator_dict.items():
            r = list(filter(lambda p: p[0] == date_obj and str(p[1]) == _indicator_task_id and str(p[2]) == _indicator_version, all_run_progress))
            if not r:
                is_completed = False
                incomplete_task_ids.add(_indicator_task_id)
            else:
                if last_finish_time:
                    last_finish_time = max(r[0][3], last_finish_time)
                else:
                    last_finish_time = r[0][3]

        if is_completed:
            completed_dates.append(formatted_date)
        
        missing_task_count = len(incomplete_task_ids)
        completed_count = total_count - missing_task_count
        incomplete_tasks = []

        for task_id in incomplete_task_ids:
                task = tasks_map.get(int(task_id))
                if task:
                    incomplete_tasks.append(IncompleteTaskInfo(
                        task_id=task.id,
                        task_code=task.task_code,
                        task_name=task.task_name,
                        object_type=task.object_type
                    ))

        recent_progress.append(DateProgressDetail(
            etl_date=formatted_date,
            completed_count=completed_count,
            total_count=total_count,
            is_complete=is_completed,
            last_finish_time=last_finish_time.isoformat() if last_finish_time else None,
            incomplete_tasks=incomplete_tasks
        ))
    
    completed_dates.sort(reverse=True)

    return WideTableVersionProgressInfo(
        version_hash=version_hash,
        wide_table_name=version.wide_table_name,
        total_indicators=len(indicator_metadata),
        completed_dates=completed_dates,
        recent_progress=recent_progress,
        lookback_days=lookback_days
    )


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