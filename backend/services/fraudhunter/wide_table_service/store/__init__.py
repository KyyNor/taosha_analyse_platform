"""
离线宽表存储后端工厂

按 fraudhunter.wide_table.offline_store 配置返回对应存储实现。
"""

from utils.config import settings
from .base import WideTableStore
from .pg_store import PgWideTableStore


def get_store(backend: str | None = None) -> WideTableStore:
    """获取离线宽表存储后端实例

    Args:
        backend: 显式后端名（postgresql）；缺省读
                 fraudhunter.wide_table.offline_store 配置。
    """
    resolved = (
        backend
        or getattr(settings, 'fraudhunter_wide_table_offline_store', 'postgresql')
        or 'postgresql'
    ).strip().lower()

    if resolved == 'postgresql':
        return PgWideTableStore()
    if resolved == 'duckdb':
        # 阶段3实现（docs/fraudhunter_offline_dual_store_plan.md）
        raise NotImplementedError("DuckDB Parquet 存储后端尚未实现（开发计划阶段3）")
    raise ValueError(f"不支持的离线宽表存储后端: {resolved}（可选: postgresql/duckdb/both）")
