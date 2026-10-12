"""delegate 模式客户端：DS 侧把 Parquet 相关操作委托给淘沙后端内部接口

背景（docs/fraudhunter_offline_dual_store_plan.md 第七章阶段 10）：离线同步在 DS（Hadoop 集群）
执行，DS 无法写淘沙机器磁盘、也访问不到 duckdb 容器端口，只能访问淘沙后端端口。
delegate 模式下 DS 只跑 Spark → PG 与 MySQL 元数据，Parquet 的探测/落盘/合并/清理
全部经本客户端调用 /api/taosha/v1/fraudhunter/internal/wide-table-store/parquet/*。

接口按业务动作设计：只传名称类参数（版本目录名、PG 表名、列名）与日期，不传 SQL、不传路径。
"""

import time
from datetime import date
from typing import Optional

import requests

from utils.config import settings
from utils.logger import logger

API_PATH = "/api/taosha/v1/fraudhunter/internal/wide-table-store"
TOKEN_HEADER = "X-Internal-Token"

# 同一目标正在被另一请求写入（服务端文件锁）时的退避重试
BUSY_RETRIES = 3
BUSY_BACKOFF_SECONDS = 10


class DelegateError(RuntimeError):
    """内部接口返回的业务错误（error_code 见服务端路由定义）"""

    def __init__(self, error_code: str, message: str, status_code: int = 0):
        super().__init__(f"[duckdb-delegate] {error_code}: {message}")
        self.error_code = error_code
        self.message = message
        self.status_code = status_code


def _cfg() -> dict:
    endpoint = (getattr(settings, 'fraudhunter_duck_compute_delegate_endpoint', '') or '').rstrip('/')
    if not endpoint:
        raise DelegateError('NOT_CONFIGURED', 'duck_compute.delegate.endpoint 未配置')
    return {
        'endpoint': endpoint,
        'token': getattr(settings, 'fraudhunter_internal_api_token', '') or '',
        'timeout': float(getattr(settings, 'fraudhunter_duck_compute_delegate_timeout_seconds', 1800)),
    }


def _post(action: str, payload: dict, sleep=time.sleep) -> dict:
    cfg = _cfg()
    url = f"{cfg['endpoint']}{API_PATH}/parquet/{action}"
    for attempt in range(BUSY_RETRIES + 1):
        started = time.perf_counter()
        try:
            resp = requests.post(
                url, json=payload, headers={TOKEN_HEADER: cfg['token']}, timeout=cfg['timeout'],
            )
        except requests.RequestException as e:
            raise DelegateError('UNREACHABLE', f"淘沙后端不可达 {url}: {e}") from e

        if resp.status_code == 200:
            logger.info(
                f"[duckdb-delegate] {action} 完成: 耗时={time.perf_counter() - started:.1f}s, "
                f"payload={_brief(payload)}"
            )
            return resp.json()

        error_code, message = _parse_error(resp)
        if error_code == 'BUSY' and attempt < BUSY_RETRIES:
            logger.warning(
                f"[duckdb-delegate] {action} 目标正被占用，{BUSY_BACKOFF_SECONDS}s 后重试 "
                f"({attempt + 1}/{BUSY_RETRIES}): {message}"
            )
            sleep(BUSY_BACKOFF_SECONDS)
            continue
        raise DelegateError(error_code, message, resp.status_code)
    raise DelegateError('BUSY', '重试次数耗尽')  # pragma: no cover - 循环内必然 return/raise


def _parse_error(resp) -> tuple:
    try:
        body = resp.json()
    except ValueError:
        return f"HTTP_{resp.status_code}", resp.text[:500]
    detail = body.get('detail', body) if isinstance(body, dict) else body
    if isinstance(detail, dict) and detail.get('error_code'):
        return detail['error_code'], str(detail.get('message', ''))
    if resp.status_code == 401:
        return 'UNAUTHORIZED', '内部接口鉴权失败：检查 fraudhunter.internal_api.token'
    return f"HTTP_{resp.status_code}", str(detail)[:500]


def _brief(payload: dict) -> dict:
    return {k: v for k, v in payload.items() if k not in ('static_cols', 'inc_cols')}


def probe(version_dir_name: str, etl_date: date) -> dict:
    """探测服务端版本目录下某日期的 Parquet：{exists, rows, error, version_dir}"""
    return _post('probe', {
        'version_dir_name': version_dir_name, 'etl_date': etl_date.isoformat(),
    })


def pull(source_pg_table: str, source_kind: str, version_dir_name: str, etl_date: date,
         expected_rows: Optional[int] = None) -> dict:
    """PG 表（staging 整表 / 正式表日期分区）→ Parquet 落盘

    Returns:
        {rows, column_count, size_bytes, final_dir, version_dir}
    """
    return _post('pull', {
        'source_pg_table': source_pg_table, 'source_kind': source_kind,
        'version_dir_name': version_dir_name, 'etl_date': etl_date.isoformat(),
        'expected_rows': expected_rows,
    })


def merge(base_version_dir_name: str, dest_version_dir_name: str, etl_date: date,
          delta_table: Optional[str], static_cols: list, inc_cols: list) -> dict:
    """增量列改写：旧版本 Parquet static 列 + PG delta 新列 → 新版本目录

    Returns:
        {rows, size_bytes, final_dir, version_dir}
    """
    return _post('merge', {
        'base_version_dir_name': base_version_dir_name,
        'dest_version_dir_name': dest_version_dir_name,
        'etl_date': etl_date.isoformat(),
        'delta_table': delta_table,
        'static_cols': list(static_cols), 'inc_cols': list(inc_cols),
    })


def cleanup(version_dir_name: str, etl_date: date) -> dict:
    """删除服务端残留的临时目录（幂等）"""
    return _post('cleanup', {
        'version_dir_name': version_dir_name, 'etl_date': etl_date.isoformat(),
    })
