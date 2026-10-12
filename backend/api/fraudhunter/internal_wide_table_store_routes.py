"""
FraudHunter 内部接口：离线宽表 Parquet 存储操作（DS delegate 模式调用）

docs/fraudhunter_offline_dual_store_plan.md 第七章阶段 10。
离线同步在 DS（Hadoop 集群）执行，DS 只能访问淘沙后端端口；Parquet 的探测/落盘/合并/清理
由本组接口在淘沙机器上完成。

鉴权：请求头 X-Internal-Token 与 fraudhunter.internal_api.token 常量时间比较；
配置为空时一律 503（默认拒绝）。不挂用户鉴权（非用户接口）。

路由函数为同步 def：FastAPI 放入线程池执行，长时间 COPY 不阻塞事件循环
（实时预警任务同样运行在 worker 的事件循环上）。
"""

import hmac
from typing import List, Optional

from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from services.fraudhunter.wide_table_service.store.parquet_ops import (
    STATUS_BY_CODE,
    ParquetOpsError,
    ParquetOpsService,
    parse_date,
)
from utils.config import settings
from utils.logger import logger

router = APIRouter(prefix="/internal/wide-table-store", tags=["内部接口-离线宽表存储"])


class InternalAuthError(Exception):
    def __init__(self, status_code: int, error_code: str, message: str):
        self.status_code, self.error_code, self.message = status_code, error_code, message


def verify_internal_token(x_internal_token: Optional[str] = Header(None)) -> None:
    expected = getattr(settings, 'fraudhunter_internal_api_token', '') or ''
    if not expected:
        raise InternalAuthError(503, 'NOT_CONFIGURED', 'fraudhunter.internal_api.token 未配置，内部接口已禁用')
    if not x_internal_token or not hmac.compare_digest(x_internal_token, expected):
        raise InternalAuthError(401, 'UNAUTHORIZED', '内部接口 token 校验失败')


class ProbeRequest(BaseModel):
    version_dir_name: str
    etl_date: str


class PullRequest(BaseModel):
    source_pg_table: str
    source_kind: str = Field(..., description="staging=整表（中转表）；partition=正式表按 etl_date 过滤")
    version_dir_name: str
    etl_date: str
    expected_rows: Optional[int] = None


class MergeRequest(BaseModel):
    base_version_dir_name: str
    dest_version_dir_name: str
    etl_date: str
    delta_table: Optional[str] = None
    static_cols: List[str] = []
    inc_cols: List[str] = []


class CleanupRequest(BaseModel):
    version_dir_name: str
    etl_date: str


def _error(status_code: int, error_code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={'detail': {
        'error_code': error_code, 'message': message,
    }})


def _run(action: str, fn):
    try:
        return fn()
    except InternalAuthError as e:
        return _error(e.status_code, e.error_code, e.message)
    except ParquetOpsError as e:
        logger.warning(f"[内部存储接口] {action} 失败: {e.error_code} {e.message}")
        return _error(STATUS_BY_CODE.get(e.error_code, 500), e.error_code, e.message)
    except Exception as e:
        logger.error(f"[内部存储接口] {action} 异常: {e}", exc_info=True)
        return _error(500, 'INTERNAL_ERROR', str(e))


def _service() -> ParquetOpsService:
    return ParquetOpsService()


@router.post("/parquet/probe", summary="探测 Parquet 日期目录（存在性 + 行数）")
def probe_parquet(req: ProbeRequest, x_internal_token: Optional[str] = Header(None)):
    def _do():
        verify_internal_token(x_internal_token)
        return _service().probe(req.version_dir_name, parse_date(req.etl_date))
    return _run('probe', _do)


@router.post("/parquet/pull", summary="PG 表 → Parquet 落盘（COPY + 对账 + 原子落盘）")
def pull_parquet(req: PullRequest, x_internal_token: Optional[str] = Header(None)):
    def _do():
        verify_internal_token(x_internal_token)
        return _service().pull(
            req.source_pg_table, req.source_kind, req.version_dir_name,
            parse_date(req.etl_date), req.expected_rows,
        )
    return _run('pull', _do)


@router.post("/parquet/merge", summary="增量列改写（旧 Parquet static 列 + PG delta 新列）")
def merge_parquet(req: MergeRequest, x_internal_token: Optional[str] = Header(None)):
    def _do():
        verify_internal_token(x_internal_token)
        return _service().merge(
            req.base_version_dir_name, req.dest_version_dir_name, parse_date(req.etl_date),
            req.delta_table, req.static_cols, req.inc_cols,
        )
    return _run('merge', _do)


@router.post("/parquet/cleanup", summary="清理残留临时目录（幂等）")
def cleanup_parquet(req: CleanupRequest, x_internal_token: Optional[str] = Header(None)):
    def _do():
        verify_internal_token(x_internal_token)
        return _service().cleanup(req.version_dir_name, parse_date(req.etl_date))
    return _run('cleanup', _do)
