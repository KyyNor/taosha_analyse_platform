"""
FraudHunter 存储后端对比：实时预警试跑（docs/fraudhunter_offline_dual_store_plan.md 第七章阶段 12）

按指定后端组装并执行一次实时模型匹配，只返回命中统计、样例与差异：
不写执行记录、不生成命中/告警/管控记录、不发消息、不写任何表（会话最终 rollback）。
全量命中明细请用 CLI 导出：python scripts/realtime_alert_dry_run.py --output hits.csv
"""

from datetime import date
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from middleware.auth_middleware import get_current_user
from models.db_base import SessionLocal
from services.fraudhunter.model_service.realtime_dry_run import (
    DryRunError,
    run_realtime_match_dry_run,
)
from services.token_service import UserInfo
from utils.logger import logger

router = APIRouter(prefix="/backend-compare", tags=["存储后端对比"])


class RealtimeMatchDryRunRequest(BaseModel):
    backend: str = Field(..., description="postgresql | duckdb | both")
    model_codes: Optional[List[str]] = Field(None, description="模型编码，默认全部在线普通模型")
    etl_date: Optional[date] = Field(None, description="离线快照日期，默认各后端最新 ready 快照")
    realtime_tables: Optional[Dict[str, str]] = Field(
        None, description="覆盖实时分区 {'dep_acct_no': 表名, 'cust_no': 表名}")
    limit: int = Field(20, ge=0, le=200, description="每个后端返回的样例行数")
    show_sql: bool = False
    tolerance: float = Field(1e-9, ge=0)


@router.post("/realtime-match", summary="实时预警试跑（只读，按后端执行模型匹配并对比）")
def realtime_match_dry_run(
    req: RealtimeMatchDryRunRequest,
    current_user: UserInfo = Depends(get_current_user),
):
    """同步 def：在线程池执行，模型匹配 SQL 耗时较长时不阻塞事件循环"""
    logger.info(
        f"[预警试跑] user={getattr(current_user, 'user_id', None)} backend={req.backend} "
        f"models={req.model_codes} etl_date={req.etl_date}"
    )
    db = SessionLocal()
    try:
        report = run_realtime_match_dry_run(
            db, req.backend, model_codes=req.model_codes, etl_date=req.etl_date,
            realtime_tables=req.realtime_tables, limit=req.limit,
            show_sql=req.show_sql, tolerance=req.tolerance,
        )
    except DryRunError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.rollback()  # 只读：任何意外变更都不落库
        db.close()

    report.pop('hits', None)  # 全量明细不经接口返回
    diff = report.get('diff')
    if diff:
        # 差异明细截断，避免响应过大
        for key in ('only_postgresql', 'only_duckdb', 'value_mismatches'):
            items = diff[key]
            diff[f'{key}_count'] = len(items)
            diff[key] = items[:max(req.limit, 1) * 5]
    return report
