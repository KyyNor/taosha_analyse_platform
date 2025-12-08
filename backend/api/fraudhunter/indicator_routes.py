"""
FraudHunter指标定义管理API路由
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from models.db_base import get_db
from schemas.fraudhunter.indicator import (
    IndicatorCreate,
    IndicatorUpdate,
    IndicatorResponse,
    IndicatorListResponse,
    PublishRequest,
)
from schemas.fraudhunter.batch_create import (
    IndicatorTaskBatchCreate,
    IndicatorBatchCreateResponse,
    CreateTaskWithIndicatorsRequest,
    CreateTaskWithIndicatorsResponse,
    TaskPreExecuteRequest,
    TaskPreExecuteResponse,
)
from services.fraudhunter.indicator_service import IndicatorManager
from utils.logger import logger


router = APIRouter(prefix="/indicators", tags=["指标管理"])


@router.post("", response_model=IndicatorResponse, summary="创建指标")
async def create_indicator(
    indicator_data: IndicatorCreate,
    db: Session = Depends(get_db)
):
    """创建新的指标定义

    参数:
    - indicator_code: 指标编码
    - indicator_name: 指标名称
    - indicator_type: 指标类型（offline/realtime）
    - data_type: 数据类型（numeric/text/date）
    - indicator_task_id: 关联的指标组ID
    """
    try:
        manager = IndicatorManager(db)
        indicator = manager.create_indicator(
            indicator_data,
            created_by="system"
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
    db: Session = Depends(get_db)
):
    """批量创建指标

    新建指标任务并批量创建指标，分两步：
    1. 先创建所有指标，获得ID列表
    2. 再创建指标任务，包含这些指标的ID

    参数:
    - indicator_type: 指标类型（所有指标共享）
    - object_type: 对象类型（所有指标共享）
    - task_data: 指标任务数据
    - indicators: 指标列表（1-50个）

    返回:
    - 批量创建结果，包含每个指标的成功/失败状态
    """
    try:
        manager = IndicatorManager(db)
        result = manager.batch_create_indicators(
            batch_data,
            created_by="system"
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
    db: Session = Depends(get_db)
):
    """在创建任务前预执行验证SQL和字段

    验证SQL逻辑是否正确，输出字段是否包含：
    - target_id
    - etl_date
    - 所有关联指标的编码字段

    Args:
        validation_request: 预执行验证请求
        db: 数据库会话

    Returns:
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
    db: Session = Depends(get_db)
):
    """创建指标任务并关联已存在的指标

    Args:
        - task_data: 指标任务数据
        - indicator_ids: 要关联的指标ID列表

    Returns:
        - 创建的任务信息和关联结果
    """
    try:
        from services.fraudhunter.indicator_service import IndicatorTaskManager

        task_manager = IndicatorTaskManager(db)

        # 创建任务
        task = task_manager.create_indicator_task(
            request_data.task_data,
            created_by="system"
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
    indicator_code: Optional[str] = Query(None, description="编码筛选（模糊匹配）"),
    query_type: Optional[str] = Query('page', description="查询类型 all为全量查询"),
    db: Session = Depends(get_db)
):
    """获取指标列表

    支持分页和多维度筛选
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
            indicator_code=indicator_code,
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
    db: Session = Depends(get_db)
):
    """获取指定ID的指标详情"""
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
    db: Session = Depends(get_db)
):
    """更新指标信息"""
    try:
        manager = IndicatorManager(db)
        indicator = manager.update_indicator(
            indicator_id,
            indicator_data,
            updated_by="system"
        )

        return indicator

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"更新指标失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新指标失败: {str(e)}")


@router.post("/{indicator_id}/publish", response_model=IndicatorResponse, summary="发布指标")
async def publish_indicator(
    indicator_id: int,
    publish_request: PublishRequest,
    db: Session = Depends(get_db)
):
    """发布指标到指定版本"""
    try:
        manager = IndicatorManager(db)
        indicator = manager.publish_indicator(
            indicator_id,
            publish_request.version,
            updated_by="system",
            change_description=publish_request.change_description
        )

        return indicator

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"发布指标失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"发布指标失败: {str(e)}")


@router.post("/{indicator_id}/archive", response_model=IndicatorResponse, summary="归档指标")
async def archive_indicator(
    indicator_id: int,
    db: Session = Depends(get_db)
):
    """归档指标"""
    try:
        manager = IndicatorManager(db)
        indicator = manager.archive_indicator(indicator_id, updated_by="system")

        return indicator

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"归档指标失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"归档指标失败: {str(e)}")


@router.delete("/{indicator_id}", summary="删除指标")
async def delete_indicator(
    indicator_id: int,
    db: Session = Depends(get_db)
):
    """删除指标（物理删除）"""
    try:
        manager = IndicatorManager(db)
        manager.delete_indicator(indicator_id)

        return {'message': f'指标 {indicator_id} 已删除'}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"删除指标失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除指标失败: {str(e)}")
