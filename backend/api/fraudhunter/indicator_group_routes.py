"""
FraudHunter指标组管理API路由
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from backend.database.db_base import get_db
from backend.schemas.fraudhunter.indicator import (
    IndicatorGroupCreate,
    IndicatorGroupUpdate,
    IndicatorGroupResponse,
    IndicatorGroupListResponse,
    DryRunRequest,
    DryRunResponse,
    PublishRequest,
)
from backend.services.fraudhunter.indicator_service import (
    IndicatorGroupManager,
    SQLValidator
)
from backend.services.fraudhunter.task_service import task_manager, indicator_executor
from utils.logger import logger


router = APIRouter(prefix="/indicator-groups", tags=["指标组管理"])


@router.post("", response_model=IndicatorGroupResponse, summary="创建指标组")
async def create_indicator_group(
    group_data: IndicatorGroupCreate,
    db: Session = Depends(get_db)
):
    """创建新的指标组

    参数:
    - group_code: 指标组编码
    - group_name: 指标组名称
    - logic_content: SQL加工逻辑
    - source_tables: 依赖的源表（逗号分隔）
    - output_table: 输出表名
    """
    try:
        # SQL验证
        validator = SQLValidator()
        validation_result = validator.validate_sql(group_data.logic_content)

        if not validation_result['valid']:
            raise HTTPException(
                status_code=400,
                detail={
                    'message': 'SQL验证失败',
                    'errors': validation_result['errors'],
                    'warnings': validation_result['warnings']
                }
            )

        # 创建指标组
        manager = IndicatorGroupManager(db)
        group = manager.create_indicator_group(
            group_data,
            created_by="system"  # 实际应该从JWT token中获取
        )

        return group

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建指标组失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建指标组失败: {str(e)}")


@router.get("", response_model=IndicatorGroupListResponse, summary="获取指标组列表")
async def list_indicator_groups(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(None, description="状态筛选"),
    group_code: Optional[str] = Query(None, description="编码筛选（模糊匹配）"),
    db: Session = Depends(get_db)
):
    """获取指标组列表

    支持分页和筛选
    """
    try:
        manager = IndicatorGroupManager(db)
        items, total = manager.list_indicator_groups(
            page=page,
            page_size=page_size,
            status=status,
            group_code=group_code
        )

        return {
            'total': total,
            'page': page,
            'page_size': page_size,
            'items': items
        }

    except Exception as e:
        logger.error(f"获取指标组列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取指标组列表失败: {str(e)}")


@router.get("/{group_id}", response_model=IndicatorGroupResponse, summary="获取指标组详情")
async def get_indicator_group(
    group_id: int,
    db: Session = Depends(get_db)
):
    """获取指定ID的指标组详情"""
    try:
        manager = IndicatorGroupManager(db)
        group = manager.get_indicator_group(group_id)

        if not group:
            raise HTTPException(status_code=404, detail=f"指标组不存在: {group_id}")

        return group

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取指标组详情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取指标组详情失败: {str(e)}")


@router.put("/{group_id}", response_model=IndicatorGroupResponse, summary="更新指标组")
async def update_indicator_group(
    group_id: int,
    group_data: IndicatorGroupUpdate,
    db: Session = Depends(get_db)
):
    """更新指标组信息

    只有draft状态的指标组才允许修改逻辑内容
    """
    try:
        # 如果更新了SQL，需要验证
        if group_data.logic_content:
            validator = SQLValidator()
            validation_result = validator.validate_sql(group_data.logic_content)

            if not validation_result['valid']:
                raise HTTPException(
                    status_code=400,
                    detail={
                        'message': 'SQL验证失败',
                        'errors': validation_result['errors'],
                        'warnings': validation_result['warnings']
                    }
                )

        manager = IndicatorGroupManager(db)
        group = manager.update_indicator_group(
            group_id,
            group_data,
            updated_by="system"
        )

        return group

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"更新指标组失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新指标组失败: {str(e)}")


@router.post("/{group_id}/dry-run", response_model=DryRunResponse, summary="指标组试运行")
async def dry_run_indicator_group(
    group_id: int,
    dry_run_request: DryRunRequest,
    db: Session = Depends(get_db)
):
    """提交指标组试运行任务

    异步执行，返回task_id用于查询进度
    """
    try:
        # 验证指标组是否存在
        manager = IndicatorGroupManager(db)
        group = manager.get_indicator_group(group_id)

        if not group:
            raise HTTPException(status_code=404, detail=f"指标组不存在: {group_id}")

        # 提交异步任务
        execution_id = await task_manager.submit_task(
            db=db,
            task_type='indicator',
            task_id=group_id,
            task_func=indicator_executor.execute_dry_run,
            created_by="system",
            group_id=group_id,
            etl_date=dry_run_request.etl_date,
            sample_size=dry_run_request.sample_size,
            group_version=dry_run_request.group_version
        )

        return {
            'task_id': execution_id,
            'status': 'pending',
            'message': '任务已提交，请通过task_id查询进度'
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"提交试运行任务失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"提交试运行任务失败: {str(e)}")


@router.post("/{group_id}/publish", response_model=IndicatorGroupResponse, summary="发布指标组")
async def publish_indicator_group(
    group_id: int,
    publish_request: PublishRequest,
    db: Session = Depends(get_db)
):
    """发布指标组到指定版本"""
    try:
        manager = IndicatorGroupManager(db)
        group = manager.publish_indicator_group(
            group_id,
            publish_request.version,
            updated_by="system",
            change_description=publish_request.change_description
        )

        return group

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"发布指标组失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"发布指标组失败: {str(e)}")


@router.post("/{group_id}/archive", response_model=IndicatorGroupResponse, summary="归档指标组")
async def archive_indicator_group(
    group_id: int,
    db: Session = Depends(get_db)
):
    """归档指标组"""
    try:
        manager = IndicatorGroupManager(db)
        group = manager.archive_indicator_group(group_id, updated_by="system")

        return group

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"归档指标组失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"归档指标组失败: {str(e)}")


@router.delete("/{group_id}", summary="删除指标组")
async def delete_indicator_group(
    group_id: int,
    db: Session = Depends(get_db)
):
    """删除指标组（物理删除）

    只能删除没有关联指标的指标组
    """
    try:
        manager = IndicatorGroupManager(db)
        manager.delete_indicator_group(group_id)

        return {'message': f'指标组 {group_id} 已删除'}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"删除指标组失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除指标组失败: {str(e)}")
