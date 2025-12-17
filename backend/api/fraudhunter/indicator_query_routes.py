"""
指标数据查询API路由
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from models.db_base import get_db
from services.fraudhunter.indicator_service import IndicatorQueryService
from schemas.fraudhunter.indicator_query import (
    IndicatorQueryRequest,
    IndicatorQueryResponse,
    IndicatorInfo
)
from utils.logger import logger

router = APIRouter(prefix="/indicator-query", tags=["指标数据查询"])


@router.get("/wide-tables", response_model=dict)
async def list_wide_table_files(
    wide_table_type: str = Query(..., description="宽表类型: dep_acct_offline, loan_acct_offline, cust_offline, dep_acct_realtime"),
    date_filter: Optional[str] = Query(None, description="日期过滤 YYYY-MM-DD"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=100, description="每页大小"),
    db: Session = Depends(get_db)
):
    """获取宽表文件列表

    支持四种宽表类型:
    - dep_acct_offline: 离线存款宽表
    - loan_acct_offline: 离线贷款宽表
    - cust_offline: 离线客户宽表
    - dep_acct_realtime: 实时存款宽表
    """
    try:
        service = IndicatorQueryService(db)
        result = service.get_wide_table_files(
            wide_table_type=wide_table_type,
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
        service = IndicatorQueryService(db)
        indicators = service.get_indicators_by_wide_table(snapshot_id)
        return indicators
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"获取指标列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取指标列表失败")


@router.post("/query", response_model=IndicatorQueryResponse)
async def query_wide_table_data(
    request: IndicatorQueryRequest,
    db: Session = Depends(get_db)
):
    """查询宽表数据"""
    try:
        service = IndicatorQueryService(db)
        result = service.query_data(request.model_dump())
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"查询数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail="查询数据失败")