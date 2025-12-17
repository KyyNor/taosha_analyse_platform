"""
指标数据查询API路由
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from services.fraudhunter.data_query_service import DataQueryService
from schemas.fraudhunter.data_query import (
    DataQueryRequest,
    DataQueryResponse,
    IndicatorInfo
)
from utils.logger import logger

router = APIRouter(prefix="/data-query", tags=["指标数据查询"])


@router.get("/wide-tables", response_model=dict)
async def list_wide_table_files(
    object_type: str = Query(..., description="对象类型"),
    date_filter: Optional[str] = Query(None, description="日期过滤 YYYY-MM-DD"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=100, description="每页大小"),
    db: Session = Depends(get_db)
):
    """获取宽表文件列表"""
    try:
        service = DataQueryService(db)
        result = service.get_wide_table_files(
            object_type=object_type,
            date_filter=date_filter,
            page=page,
            page_size=page_size
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"获取宽表文件列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取宽表文件列表失败")


@router.get("/indicators/{snapshot_id}", response_model=list[IndicatorInfo])
async def get_indicators_by_snapshot(
    snapshot_id: int,
    db: Session = Depends(get_db)
):
    """根据快照ID获取指标列表"""
    try:
        service = DataQueryService(db)
        indicators = service.get_indicators_by_wide_table(snapshot_id)
        return indicators
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"获取指标列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取指标列表失败")


@router.post("/query", response_model=DataQueryResponse)
async def query_wide_table_data(
    request: DataQueryRequest,
    db: Session = Depends(get_db)
):
    """查询宽表数据"""
    try:
        service = DataQueryService(db)
        result = service.query_data(request.model_dump())
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"查询数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail="查询数据失败")