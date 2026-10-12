"""
离线宽表存储后端工厂

按 fraudhunter.wide_table.offline_store 配置返回对应存储实现：
- postgresql: PG 正式表（现状路径）
- duckdb:     本地 Parquet 目录（staging 中转）
- both:       灰度双写（同步入口串行执行两后端，各自独立快照）
"""

from utils.config import settings
from .base import WideTableStore
from .pg_store import PgWideTableStore

VALID_BACKENDS = ('postgresql', 'duckdb', 'both')


def _resolve_backend(backend: str | None) -> str:
    resolved = (
        backend
        or getattr(settings, 'fraudhunter_wide_table_offline_store', 'postgresql')
        or 'postgresql'
    ).strip().lower()
    if resolved not in VALID_BACKENDS:
        raise ValueError(
            f"不支持的离线宽表存储后端: {resolved}（可选: {'/'.join(VALID_BACKENDS)}）"
        )
    return resolved


def get_store(backend: str | None = None) -> WideTableStore:
    """获取单个离线宽表存储后端实例"""
    resolved = _resolve_backend(backend)

    if resolved == 'postgresql':
        return PgWideTableStore()
    if resolved == 'duckdb':
        from .duckdb_parquet_store import DuckdbParquetStore
        return DuckdbParquetStore()
    # both 由 resolve_stores 拆分，不作为单store返回
    raise ValueError("both 模式请使用 resolve_stores() 获取后端列表")


def resolve_stores(backend: str | None = None) -> list[WideTableStore]:
    """获取同步入口要执行的后端列表（both → PG先、Parquet后 串行）"""
    resolved = _resolve_backend(backend)
    if resolved == 'both':
        from .duckdb_parquet_store import DuckdbParquetStore
        return [PgWideTableStore(), DuckdbParquetStore()]
    return [get_store(resolved)]
