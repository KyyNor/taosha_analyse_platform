"""
FraudHunter指标任务管理API路由
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from middleware.auth_middleware import get_current_user
from models.db_base import get_db
from schemas.fraudhunter.indicator import (
    DryRunRequest,
    DryRunResponse,
    IndicatorTaskCreate,
    IndicatorTaskListResponse,
    IndicatorTaskResponse,
    IndicatorTaskUpdate,
    PublishToDSRequest,
    PublishToDSResponse,
    RerunRequest,
    RerunResponse,
)
from services.fraudhunter.dry_run_task_service import dry_run_task_manager, indicator_executor
from services.fraudhunter.indicator_service import (
    IndicatorTaskManager,
    SQLValidator,
)
from services.token_service import UserInfo
from utils.logger import logger


router = APIRouter(prefix="/indicator-tasks", tags=["指标任务管理"])


@router.post("", summary="创建指标任务")
async def create_indicator_task(
    task_data: IndicatorTaskCreate,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user),
):
    """创建新的指标任务

    参数:
        task_data: 包含 task_code, task_name, logic_content, source_tables

    返回:
        success=True 时: {success: true, data: IndicatorTask}
        success=False 时: {success: false, message: str, errors: list}
    """
    try:
        # SQL验证
        validator = SQLValidator()
        validation_result = validator.validate_sql(task_data.logic_content)

        if not validation_result['valid']:
            # 返回200状态码，但包含错误信息
            return {
                'success': False,
                'message': 'SQL验证失败',
                'errors': validation_result['errors']
            }

        # 创建指标任务
        manager = IndicatorTaskManager(db)
        task = manager.create_indicator_task(
            task_data,
            created_by=current_user.user_id
        )

        return {
            'success': True,
            'data': task
        }

    except ValueError as e:
        return {
            'success': False,
            'message': str(e),
            'errors': [str(e)]
        }
    except Exception as e:
        logger.error(f"创建指标任务失败: {e!r}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建指标任务失败: {str(e)}")


@router.get("", response_model=IndicatorTaskListResponse, summary="获取指标任务列表")
async def list_indicator_tasks(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(None, description="状态筛选"),
    search: Optional[str] = Query(None, description="搜索（模糊匹配编码和名称）"),
    object_type: Optional[str] = Query(None, description="对象类型筛选"),
    db: Session = Depends(get_db),
) -> IndicatorTaskListResponse:
    """获取指标任务列表，支持分页和筛选

    参数:
        page: 页码
        page_size: 每页数量
        status: 状态筛选
        search: 搜索关键字（模糊匹配编码和名称）
        object_type: 对象类型筛选

    返回:
        包含 total, page, page_size, items 的分页结果
    """
    try:
        manager = IndicatorTaskManager(db)
        items, total = manager.list_indicator_tasks(
            page=page,
            page_size=page_size,
            status=status,
            search_query=search,  # 修改：使用search_query参数
            object_type=object_type
        )

        return {
            'total': total,
            'page': page,
            'page_size': page_size,
            'items': items
        }

    except Exception as e:
        logger.error(f"获取指标任务列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取指标任务列表失败: {str(e)}")


@router.get("/{task_id}", response_model=IndicatorTaskResponse, summary="获取指标任务详情")
async def get_indicator_task(
    task_id: int,
    db: Session = Depends(get_db),
) -> IndicatorTaskResponse:
    """获取指定ID的指标任务详情

    参数:
        task_id: 指标任务ID

    返回:
        指标任务详情

    异常:
        404: 指标任务不存在
    """
    try:
        manager = IndicatorTaskManager(db)
        task = manager.get_indicator_task(task_id)

        if not task:
            raise HTTPException(status_code=404, detail=f"指标任务不存在: {task_id}")

        return task

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取指标任务详情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取指标任务详情失败: {str(e)}")


@router.put("/{task_id}", summary="更新指标任务")
async def update_indicator_task(
    task_id: int,
    task_data: IndicatorTaskUpdate,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user),
):
    """更新指标任务信息

    注意：只有draft状态的指标任务才允许修改逻辑内容

    参数:
        task_id: 指标任务ID
        task_data: 更新数据

    返回:
        success=True 时: {success: true, data: IndicatorTask}
        success=False 时: {success: false, message: str, errors: list}
    """
    try:
        # 如果更新了SQL，需要验证
        if task_data.logic_content:
            validator = SQLValidator()
            validation_result = validator.validate_sql(task_data.logic_content)

            if not validation_result['valid']:
                # 返回200状态码，但包含错误信息
                return {
                    'success': False,
                    'message': 'SQL验证失败',
                    'errors': validation_result['errors']
                }

        manager = IndicatorTaskManager(db)
        task = manager.update_indicator_task(
            task_id,
            task_data,
            updated_by=current_user.user_id
        )

        return {
            'success': True,
            'data': task
        }

    except ValueError as e:
        return {
            'success': False,
            'message': str(e),
            'errors': [str(e)]
        }
    except Exception as e:
        logger.error(f"更新指标任务失败: {e!r}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新指标任务失败: {str(e)}")


@router.post("/{task_id}/dry-run", response_model=DryRunResponse, summary="指标任务试运行")
async def dry_run_indicator_task(
    task_id: int,
    dry_run_request: DryRunRequest,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user),
) -> DryRunResponse:
    """提交指标任务试运行任务（异步执行）

    参数:
        task_id: 指标任务ID
        dry_run_request: 试运行请求参数

    返回:
        包含 task_id 的执行信息，用于查询进度
    """
    try:
        # 验证指标任务是否存在
        manager = IndicatorTaskManager(db)
        task = manager.get_indicator_task(task_id)

        if not task:
            raise HTTPException(status_code=404, detail=f"指标任务不存在: {task_id}")

        # 提交异步任务
        execution_id = await dry_run_task_manager.submit_task(
            db=db,
            task_type='indicator',
            task_id=task_id,
            task_func=indicator_executor.execute_dry_run,
            created_by=current_user.user_id,
            etl_date=dry_run_request.etl_date,
            sample_size=dry_run_request.sample_size,
            task_version=dry_run_request.task_version
        )

        return {
            "task_id": execution_id,
            "status": "pending",
            "message": "任务已提交，请通过task_id查询进度"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"提交试运行任务失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"提交试运行任务失败: {str(e)}")

@router.delete("/{task_id}", summary="删除指标任务")
async def delete_indicator_task(
    task_id: int,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """删除指标任务（物理删除）

    注意：只能删除没有关联指标的指标任务

    参数:
        task_id: 指标任务ID

    返回:
        删除成功消息
    """
    try:
        manager = IndicatorTaskManager(db)
        manager.delete_indicator_task(task_id)

        return {"message": f"指标任务 {task_id} 已删除"}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"删除指标任务失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除指标任务失败: {str(e)}")


# ==================== DolphinScheduler 相关接口 ====================

@router.post("/{task_id}/publish-to-ds", response_model=PublishToDSResponse, summary="上线到DolphinScheduler")
async def publish_to_dolphinscheduler(
    task_id: int,
    request: PublishToDSRequest,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user),
) -> PublishToDSResponse:
    """将指标任务上线到 DolphinScheduler

    参数:
        task_id: 指标任务ID
        request: 上线请求参数

    返回:
        PublishToDSResponse: 上线结果
    """
    try:
        from services.dolphinscheduler import DolphinSchedulerService
        from services.fraudhunter.wide_table_service.version_manager import WideTableVersionManager

        # 验证指标任务是否存在
        manager = IndicatorTaskManager(db)
        indicator_task = manager.get_indicator_task(task_id)

        if not indicator_task:
            raise HTTPException(status_code=404, detail=f"指标任务不存在: {task_id}")

        indicators = indicator_task.indicators
        if not indicators:
            raise HTTPException(
                status_code=400,
                detail=f"指标任务 {task_id} 没有关联的指标，无法上线"
            )

        # 提交到 DolphinScheduler
        ds_service = DolphinSchedulerService()
        result = ds_service.submit_indicator_task_workflow(indicator_task, db)

        # 更新数据库中的 DS 任务信息和状态
        indicator_task.ds_task_name = result.get("workflow_name")
        indicator_task.ds_task_code = result.get("workflow_code")

        if result.get("success", False):
            indicator_task.status = "online"
            indicator_task.current_version = indicator_task.latest_version
            # 同步更新关联指标状态
            for indicator in indicators:
                indicator.status = "online"
                indicator.current_version = indicator.latest_version
            logger.info(f"已同步更新 {len(indicators)} 个指标的状态和 current_version")

        db.commit()
        db.refresh(indicator_task)

        # 触发宽表版本变更检查（不影响主流程）
        try:
            version_manager = WideTableVersionManager(db)
            version_manager.create_new_version(
                indicator_task.object_type,
                created_by=current_user.user_id
            )
            logger.info(f"已触发 object_type={indicator_task.object_type} 的宽表版本变更检查")
        except Exception as e:
            logger.error(f"触发宽表版本变更检查失败: {e}", exc_info=True)

        logger.info(f"指标任务 {task_id} 已成功上线到 DolphinScheduler")

        return PublishToDSResponse(
            success=True,
            message="指标任务已成功上线到 DolphinScheduler",
            workflow_name=result.get("workflow_name"),
            workflow_code=result.get("workflow_code"),
            ds_task_name=result.get("ds_task_name"),
            ds_task_code=result.get("ds_task_code"),
            online_success=result.get("online_success", False)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上线到 DolphinScheduler 失败: {e}", exc_info=True)
        return PublishToDSResponse(
            success=False,
            message=f"上线失败: {str(e)}",
            workflow_name=None,
            workflow_code=None,
            ds_task_name=None,
            ds_task_code=None,
            online_success=False
        )


@router.post("/{task_id}/rerun", response_model=RerunResponse, summary="补数")
async def rerun_indicator_task(
    task_id: int,
    request: RerunRequest,
    db: Session = Depends(get_db),
) -> RerunResponse:
    """对指标任务进行补数

    参数:
        task_id: 指标任务ID
        request: 补数请求参数（开始日期、结束日期）

    返回:
        RerunResponse: 补数结果
    """
    try:
        from services.dolphinscheduler import DolphinSchedulerService

        # 验证指标任务是否存在
        manager = IndicatorTaskManager(db)
        indicator_task = manager.get_indicator_task(task_id)

        if not indicator_task:
            raise HTTPException(status_code=404, detail=f"指标任务不存在: {task_id}")

        # 处理结束日期（默认为今天）
        end_date = request.end_date or datetime.now().strftime("%Y-%m-%d")

        # 执行补数
        ds_service = DolphinSchedulerService()
        result = ds_service.run_backfill(
            workflow_code=indicator_task.ds_task_code,
            start_date=request.start_date,
            end_date=end_date
        )

        logger.info(f"指标任务 {task_id} 补数任务已提交: {request.start_date} - {end_date}")

        return RerunResponse(
            success=result.get("success", True),
            message=result.get("message", "补数任务已提交"),
            workflow_code=indicator_task.ds_task_code,
            start_date=request.start_date,
            end_date=end_date
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"补数任务失败: {e}", exc_info=True)
        return RerunResponse(
            success=False,
            message=f"补数失败: {str(e)}",
            workflow_code=None,
            start_date=request.start_date,
            end_date=request.end_date
        )
