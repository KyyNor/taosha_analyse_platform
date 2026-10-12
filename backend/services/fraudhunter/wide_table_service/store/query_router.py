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


VALID_WRITE_BACKENDS = ('postgresql', 'duckdb', 'both')
VALID_READ_BACKENDS = ('postgresql', 'duckdb')
VALID_COMPUTE_MODES = ('local', 'remote', 'delegate')


def resolve_read_backend(offline_store: Optional[str], read_backend: Optional[str]) -> str:
    """读后端推导（二期阶段 9，读写分离）

    - 显式配置 read_backend → 按配置；
    - 未配置 → offline_store=duckdb 读 duckdb，其余（postgresql/both）读 postgresql。
      注意 both 未配置读后端时读 PG（影子写），一期 both 读 duckdb 的语义已有意修正。
    """
    if read_backend:
        return str(read_backend).strip().lower()
    return 'duckdb' if (offline_store or 'postgresql').strip().lower() == 'duckdb' else 'postgresql'


def validate_store_config(
    offline_store: Optional[str],
    read_backend: Optional[str],
    compute_mode: Optional[str] = 'local',
    role: str = 'backend',
) -> list:
    """校验存储读写配置组合；非法组合抛 ValueError，可运行但有风险的组合返回告警列表

    Args:
        role: backend=淘沙后端进程；ds=DS 离线同步入口
    """
    write = (offline_store or 'postgresql').strip().lower()
    read = resolve_read_backend(write, read_backend)
    mode = (compute_mode or 'local').strip().lower()
    warnings = []

    if write not in VALID_WRITE_BACKENDS:
        raise ValueError(f"offline_store 取值非法: {write}（可选: {'/'.join(VALID_WRITE_BACKENDS)}）")
    if read not in VALID_READ_BACKENDS:
        raise ValueError(f"read_backend 取值非法: {read}（可选: {'/'.join(VALID_READ_BACKENDS)}）")
    if mode not in VALID_COMPUTE_MODES:
        raise ValueError(f"duck_compute.mode 取值非法: {mode}（可选: {'/'.join(VALID_COMPUTE_MODES)}）")
    if write == 'postgresql' and read == 'duckdb':
        raise ValueError("offline_store=postgresql 不会产生 duckdb 快照，read_backend 不能为 duckdb")
    if role == 'backend' and mode == 'delegate':
        raise ValueError("duck_compute.mode=delegate 仅用于 DS 离线同步入口，淘沙后端请配置 local 或 remote")
    if write == 'duckdb' and read == 'postgresql':
        warnings.append("offline_store=duckdb 且 read_backend=postgresql：PG 离线数据将停止更新，读到的是切换前的旧快照")
    return warnings


def preferred_snapshot_backend() -> str:
    """当前配置偏好的快照存储后端（读后端，Issue #9 统一策略防各调用点漂移）"""
    return resolve_read_backend(
        getattr(settings, 'fraudhunter_wide_table_offline_store', 'postgresql'),
        getattr(settings, 'fraudhunter_wide_table_read_backend', None),
    )


def offline_store_uses_duckdb() -> bool:
    """离线存储（写）配置是否含 DuckDB（DuckDB 专属维护任务的启用条件，Issue #10）"""
    return getattr(
        settings, 'fraudhunter_wide_table_offline_store', 'postgresql',
    ) in ('duckdb', 'both')


def select_snapshot_by_preferred_backend(snapshots) -> Optional[object]:
    """按配置偏好从（已按新→旧排序的）快照列表中选择一条

    优先返回 preferred_snapshot_backend()（读后端）对应的快照；读后端
    完全没有快照时回退最新一条并告警（例如读切回 postgresql 但
    PG 侧尚未补数时，避免直接不可用）。
    """
    snapshots = [s for s in snapshots if s is not None]
    if not snapshots:
        return None
    preferred = preferred_snapshot_backend()
    for s in snapshots:
        if snapshot_backend(s) == preferred:
            return s
    fallback = snapshots[0]
    logger.warning(
        f"[快照选择] 未找到读后端（read_backend={preferred}）的快照，回退使用 "
        f"{snapshot_backend(fallback)} 快照（generation_time={getattr(fallback, 'generation_time', None)}）"
    )
    return fallback


def requires_duckdb(*snapshots) -> bool:
    """判断快照集中是否含 duckdb 快照（决定执行引擎）"""
    return any(snapshot_backend(s) == 'duckdb' for s in snapshots if s is not None)


def resolve_offline_table_refs(snapshots: dict) -> tuple:
    """统一解析离线快照表引用（混合后端安全，PR#12 评论#2）

    流程：先按全部快照判定一次 duckdb_mode，再统一生成表引用——
    duckdb_mode 下 postgresql 快照必须走 pg_rt.public.* 前缀，
    避免混合快照（如 dep_acct=PG、cust=duckdb）时裸 PG 表名
    在 DuckDB 执行引擎下找不到表。

    Args:
        snapshots: {object_type: 快照或None}（如 {'dep_acct_no': snap, 'cust_no': snap}）

    Returns:
        ({object_type: SQL表引用或None}, duckdb_mode)
    """
    items = dict(snapshots or {})
    duckdb_mode = requires_duckdb(*items.values())
    refs = {
        key: (
            None if snap is None
            else offline_table_ref(snap, snap.etl_date, duckdb_mode=duckdb_mode)
        )
        for key, snap in items.items()
    }
    return refs, duckdb_mode


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
