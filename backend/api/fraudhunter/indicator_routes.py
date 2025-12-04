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
    - data_type: 数据类型（numeric/enum/text/boolean）
    - indicator_group_id: 关联的指标组ID
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


@router.get("", response_model=IndicatorListResponse, summary="获取指标列表")
async def list_indicators(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(None, description="状态筛选"),
    indicator_type: Optional[str] = Query(None, description="指标类型筛选"),
    indicator_group_id: Optional[int] = Query(None, description="指标组ID筛选"),
    indicator_code: Optional[str] = Query(None, description="编码筛选（模糊匹配）"),
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
            indicator_group_id=indicator_group_id,
            indicator_code=indicator_code
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
