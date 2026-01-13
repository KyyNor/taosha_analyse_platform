"""
FraudHunter指标定义管理API路由
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from middleware.auth_middleware import get_current_user
from models.db_base import get_db
from schemas.fraudhunter.batch_create import (
    CreateTaskWithIndicatorsRequest,
    CreateTaskWithIndicatorsResponse,
    IndicatorBatchCreateResponse,
    IndicatorTaskBatchCreate,
    TaskPreExecuteRequest,
    TaskPreExecuteResponse,
)
from schemas.fraudhunter.indicator import (
    IndicatorCreate,
    IndicatorListResponse,
    IndicatorResponse,
    IndicatorUpdate,
    PublishRequest,
)
from services.fraudhunter.indicator_service import IndicatorManager
from services.token_service import UserInfo
from utils.logger import logger


router = APIRouter(prefix="/indicators", tags=["指标管理"])


@router.post("", response_model=IndicatorResponse, summary="创建指标")
async def create_indicator(
    indicator_data: IndicatorCreate,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user),
) -> IndicatorResponse:
    """创建新的指标定义

    参数:
        indicator_data: 包含 indicator_code, indicator_name, indicator_type,
                       data_type, indicator_task_id 等字段

    返回:
        创建的指标信息
    """
    try:
        manager = IndicatorManager(db)
        indicator = manager.create_indicator(
            indicator_data,
            created_by=current_user.user_id
        )

        return indicator

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建指标失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建指标失败: {str(e)}")


@router.post("/batch", response_model=IndicatorBatchCreateResponse, summary="批量创建指标")
async def batch_create_indicators(
    batch_data: IndicatorTaskBatchCreate,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user),
) -> IndicatorBatchCreateResponse:
    """批量创建指标

    流程说明：
        1. 先创建所有指标，获得ID列表
        2. 再创建指标任务，包含这些指标的ID

    参数:
        batch_data: 包含 indicator_type, object_type, task_data, indicators

    返回:
        批量创建结果，包含每个指标的成功/失败状态
    """
    try:
        manager = IndicatorManager(db)
        result = manager.batch_create_indicators(
            batch_data,
            created_by=current_user.user_id
        )

        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"批量创建指标失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"批量创建指标失败: {str(e)}")


@router.post("/batch/validate-task", response_model=TaskPreExecuteResponse, summary="预执行验证任务")
async def validate_task_before_create(
    validation_request: TaskPreExecuteRequest,
    db: Session = Depends(get_db),
) -> TaskPreExecuteResponse:
    """在创建任务前预执行验证SQL和字段

    验证内容：
        - SQL逻辑是否正确
        - 输出字段是否包含：target_id, etl_date, 所有关联指标的编码字段

    参数:
        validation_request: 预执行验证请求

    返回:
        验证结果，包含字段验证详情和样本数据
    """
    try:
        from services.fraudhunter.dry_run_task_service import indicator_executor

        # 执行预验证
        validation_result = await indicator_executor.validate_task_logic(
            db=db,
            task_data=validation_request.task_data,
            indicator_ids=validation_request.indicator_ids,
            etl_date=validation_request.etl_date,
            sample_size=10  # 验证时使用小样本
        )

        # 检查字段验证是否通过
        field_validation = validation_result['field_validation']
        if not field_validation['valid']:
            return TaskPreExecuteResponse(
                success=False,
                message=f"字段验证失败，缺失字段: {', '.join(field_validation['missing_fields'])}",
                validation_details=field_validation
            )

        return TaskPreExecuteResponse(
            success=True,
            message="预执行验证通过，SQL逻辑正确，字段完整",
            sample_result=validation_result['sample_result'],
            validation_details=validation_result
        )

    except ValueError as e:
        return TaskPreExecuteResponse(
            success=False,
            message=str(e)
        )
    except Exception as e:
        logger.error(f"预执行验证失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"预执行验证失败: {str(e)}")


@router.post("/batch/create-task", response_model=CreateTaskWithIndicatorsResponse, summary="创建任务并关联指标")
async def create_task_with_indicators(
    request_data: CreateTaskWithIndicatorsRequest,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user),
) -> CreateTaskWithIndicatorsResponse:
    """创建指标任务并关联已存在的指标

    参数:
        request_data: 包含 task_data 和 indicator_ids

    返回:
        创建的任务信息和关联结果
    """
    try:
        from services.fraudhunter.indicator_service import IndicatorTaskManager

        task_manager = IndicatorTaskManager(db)

        # 创建任务
        task = task_manager.create_indicator_task(
            request_data.task_data,
            created_by=current_user.user_id
        )

        # 关联指标到任务
        if request_data.indicator_ids:
            from models.fraudhunter.indicator import FraudHunterIndicatorDefinition

            # 批量更新指标的indicator_task_id
            db.query(FraudHunterIndicatorDefinition).filter(
                FraudHunterIndicatorDefinition.id.in_(request_data.indicator_ids)
            ).update(
                {"indicator_task_id": task.id},
                synchronize_session=False
            )

            logger.info(f"已将 {len(request_data.indicator_ids)} 个指标关联到任务 {task.task_code}")

        return CreateTaskWithIndicatorsResponse(
            task_id=task.id,
            task_code=task.task_code,
            task_name=task.task_name,
            indicator_count=len(request_data.indicator_ids),
            indicator_ids=request_data.indicator_ids
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建任务并关联指标失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建任务并关联指标失败: {str(e)}")


@router.get("", response_model=IndicatorListResponse, summary="获取指标列表")
async def list_indicators(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(None, description="状态筛选"),
    indicator_type: Optional[str] = Query(None, description="指标类型筛选"),
    object_type: Optional[str] = Query(None, description="对象类型筛选"),
    indicator_task_id: Optional[int] = Query(None, description="指标组ID筛选"),
    search: Optional[str] = Query(None, description="搜索（模糊匹配指标编码和名称）"),
    query_type: Optional[str] = Query("page", description="查询类型，all为全量查询"),
    db: Session = Depends(get_db),
) -> IndicatorListResponse:
    """获取指标列表，支持分页和多维度筛选

    参数:
        page: 页码
        page_size: 每页数量
        status: 状态筛选
        indicator_type: 指标类型筛选
        object_type: 对象类型筛选
        indicator_task_id: 指标组ID筛选
        search: 搜索关键字（模糊匹配指标编码和名称）
        query_type: 查询类型，page为分页查询，all为全量查询

    返回:
        包含 total, page, page_size, items 的分页结果
    """
    try:
        manager = IndicatorManager(db)
        items, total = manager.list_indicators(
            page=page,
            page_size=page_size,
            status=status,
            indicator_type=indicator_type,
            object_type=object_type,
            indicator_task_id=indicator_task_id,
            search_query=search,  # 修改：使用search_query参数
            query_type=query_type
        )

        return {
            'total': total,
            'page': page,
            'page_size': page_size,
            'items': items
        }

    except Exception as e:
        logger.error(f"获取指标列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取指标列表失败: {str(e)}")


@router.get("/{indicator_id}", response_model=IndicatorResponse, summary="获取指标详情")
async def get_indicator(
    indicator_id: int,
    db: Session = Depends(get_db),
) -> IndicatorResponse:
    """获取指定ID的指标详情

    参数:
        indicator_id: 指标ID

    返回:
        指标详情

    异常:
        404: 指标不存在
    """
    try:
        manager = IndicatorManager(db)
        indicator = manager.get_indicator(indicator_id)

        if not indicator:
            raise HTTPException(status_code=404, detail=f"指标不存在: {indicator_id}")

        return indicator

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取指标详情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取指标详情失败: {str(e)}")


@router.put("/{indicator_id}", response_model=IndicatorResponse, summary="更新指标")
async def update_indicator(
    indicator_id: int,
    indicator_data: IndicatorUpdate,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user),
) -> IndicatorResponse:
    """更新指标信息

    参数:
        indicator_id: 指标ID
        indicator_data: 更新数据

    返回:
        更新后的指标信息
    """
    try:
        manager = IndicatorManager(db)
        indicator = manager.update_indicator(
            indicator_id,
            indicator_data,
            updated_by=current_user.user_id
        )

        return indicator

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"更新指标失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新指标失败: {str(e)}")


@router.post("/{indicator_id}/archive", response_model=IndicatorResponse, summary="归档指标")
async def archive_indicator(
    indicator_id: int,
    db: Session = Depends(get_db),
    current_user: UserInfo = Depends(get_current_user),
) -> IndicatorResponse:
    """归档指标

    参数:
        indicator_id: 指标ID

    返回:
        归档后的指标信息
    """
    try:
        manager = IndicatorManager(db)
        indicator = manager.archive_indicator(indicator_id, updated_by=current_user.user_id)

        return indicator

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"归档指标失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"归档指标失败: {str(e)}")


@router.delete("/{indicator_id}", summary="删除指标")
async def delete_indicator(
    indicator_id: int,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """删除指标（物理删除）

    参数:
        indicator_id: 指标ID

    返回:
        删除成功消息
    """
    try:
        manager = IndicatorManager(db)
        manager.delete_indicator(indicator_id)

        return {"message": f"指标 {indicator_id} 已删除"}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"删除指标失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除指标失败: {str(e)}")
