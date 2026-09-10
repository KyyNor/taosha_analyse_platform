"""
查询路由层

双存储方案阶段4（docs/fraudhunter_offline_dual_store_plan.md）：
指标查询/回测/实时任务按快照 storage_backend 决定：
- 表引用：postgresql 快照 → PG分区表名（现状公式，行为不变）；
          duckdb 快照 → read_parquet glob（hive_partitioning=false，etl_date为文件物理列）
- 执行引擎：全部 postgresql → 现状 PG 路径（AnalyzeDBConnector）；
           任一 duckdb → DuckDB 执行，PG 侧表（实时表/PG离线表）经 ATTACH 别名 pg_rt 引用

实时表查询经 postgres 扩展访问时必须携带日期过滤（谓词下推前提），
回测/实时任务SQL均按日期分区引用，天然满足。
"""

from pathlib import Path
from typing import Optional

from utils.config import settings
from utils.logger import logger

# DuckDB ATTACH 的 PG 只读别名（实时表与PG侧离线表统一经此引用）
PG_ATTACH_ALIAS = 'pg_rt'


def snapshot_backend(snapshot) -> str:
    """读取快照存储后端（缺省 postgresql 兜底，兼容未迁移存量行）"""
    return getattr(snapshot, 'storage_backend', None) or 'postgresql'


def requires_duckdb(*snapshots) -> bool:
    """判断快照集中是否含 duckdb 快照（决定执行引擎）"""
    return any(snapshot_backend(s) == 'duckdb' for s in snapshots if s is not None)


def offline_table_ref(snapshot, etl_date, duckdb_mode: bool = False) -> str:
    """离线宽表快照的 SQL 表引用

    Args:
        snapshot: FraudHunterWideTableSnapshot（或含同名属性的选择结果）
        etl_date: 数据日期
        duckdb_mode: DuckDB 执行模式下，PG 侧表引用带 ATTACH 前缀
    """
    backend = snapshot_backend(snapshot)
    if backend == 'duckdb' and snapshot.parquet_file_path:
        glob = Path(snapshot.parquet_file_path) / f"etl_date={etl_date.strftime('%Y-%m-%d')}" / "*.parquet"
        return f"read_parquet('{glob.as_posix()}', hive_partitioning=false)"

    pg_name = pg_partition_name(
        wide_table_name=snapshot.wide_table_name,
        version_hash=snapshot.version_hash,
        etl_date=etl_date,
    )
    if duckdb_mode:
        return f"{PG_ATTACH_ALIAS}.public.{pg_name}"
    return pg_name


def pg_partition_name(wide_table_name: str, version_hash: Optional[str], etl_date) -> str:
    """PG 分区表名（沿用回测/实时任务现有公式，PG模式行为不变）"""
    return f"{wide_table_name}_{version_hash}_{etl_date.strftime('%Y%m%d')}"


def realtime_table_ref(table_name: Optional[str], duckdb_mode: bool = False) -> Optional[str]:
    """实时宽表 PG 表引用（实时链路永久在 PG，duckdb 模式下经 ATTACH 别名）"""
    if not table_name:
        return None
    if duckdb_mode:
        return f"{PG_ATTACH_ALIAS}.public.{table_name}"
    return table_name


def _pg_attach_conn_string() -> str:
    pg = settings.fraudhunter_analyze_db['postgresql']
    conn_string = (
        f"dbname={pg['database']} host={pg['host']} port={pg['port']} "
        f"user={pg['user']} password={pg['password']}"
    )
    return conn_string.replace("\\", "\\\\").replace("'", "\\'")


def attach_postgres(conn) -> None:
    """在给定 DuckDB 连接上 ATTACH PG（READ_ONLY，别名 pg_rt）"""
    conn.execute("LOAD postgres;")
    conn.execute(
        f"ATTACH '{_pg_attach_conn_string()}' AS {PG_ATTACH_ALIAS} (TYPE POSTGRES, READ_ONLY);"
    )


def get_query_session(attach_pg: bool = True):
    """查询会话工厂：按 duck_compute.mode 返回本地/远程会话（同构接口）

    - local（默认）: DuckQuerySession，进程内 import duckdb（现状，行为不变）
    - remote: RemoteDuckSession，经 HTTP 网关调用 duckdb 容器
      （后端机器 glibc < 2.27 装不了 duckdb 时使用，见 docs/duckdb_remote_compute_plan.md）
    """
    mode = getattr(settings, 'fraudhunter_duck_compute_mode', 'local')
    if mode == 'remote':
        from services.fraudhunter.wide_table_service.store.remote_session import (
            RemoteDuckSession,
        )
        return RemoteDuckSession(attach_pg=attach_pg)
    return DuckQuerySession(attach_pg=attach_pg)


class DuckQuerySession:
    """DuckDB 查询会话（上下文管理器）

    - attach_pg=True:  ATTACH PG 只读（需要 JOIN 实时表/PG侧表的场景）
    - attach_pg=False: 纯本地 Parquet 查询（如数据预览）
    """

    def __init__(self, attach_pg: bool = True):
        self._attach_pg = attach_pg
        self.conn = None

    def __enter__(self):
        import duckdb

        self.conn = duckdb.connect()
        try:
            if self._attach_pg:
                attach_postgres(self.conn)
        except Exception:
            self.conn.close()
            self.conn = None
            raise
        return self

    def execute_df(self, sql: str):
        """执行查询并返回 pandas DataFrame（失败返回 None，与 AnalyzeDBConnector 行为对齐）"""
        logger.debug(f"[duckdb查询] {sql[:500]}")
        return self.conn.execute(sql).fetchdf()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn is not None:
            if self._attach_pg:
                try:
                    self.conn.execute(f"DETACH {PG_ATTACH_ALIAS}")
                except Exception:
                    pass
            self.conn.close()
            self.conn = None
        return False
