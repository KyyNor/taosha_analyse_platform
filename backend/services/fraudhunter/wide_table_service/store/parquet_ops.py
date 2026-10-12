"""淘沙侧 Parquet 存储操作（内部接口的服务层，二期阶段 10）

DS 以 delegate 模式调用 /fraudhunter/internal/wide-table-store/parquet/*，本模块在淘沙机器上
执行对应动作，内部复用 DuckdbParquetStore 现有的 local/remote 实现（COPY/对账/原子落盘不重写）。

安全约束（接口不走用户鉴权，靠共享 token + 以下约束收敛暴露面）：
- 不接受 SQL、不接受路径：目录由 storage_path + 版本目录名 + 日期拼接；
- 名称类参数（版本目录名、PG 表名、列名）必须匹配 ^[a-z0-9_]+$ 且长度 ≤ 128；
- 拼出的路径 resolve 后必须位于 storage_path 之下；
- 同一目标日期目录加文件锁（fcntl，跨 uvicorn worker 有效），抢不到锁返回 BUSY。
"""

import fcntl
import os
import re
import shutil
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Optional

from utils.logger import logger

NAME_RE = re.compile(r'^[a-z0-9_]{1,128}$')
DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')


class ParquetOpsError(RuntimeError):
    """内部接口业务错误：error_code 对应 HTTP 状态码见 STATUS_BY_CODE"""

    def __init__(self, error_code: str, message: str):
        super().__init__(message)
        self.error_code = error_code
        self.message = message


STATUS_BY_CODE = {
    'INVALID_ARGUMENT': 422,
    'RECONCILE_FAILED': 422,
    'NOT_FOUND': 404,
    'TARGET_UNIVERSE_CHANGED': 409,
    'BUSY': 409,
    'NOT_CONFIGURED': 503,
}


def validate_name(value: Optional[str], field: str) -> str:
    if value is None or not NAME_RE.match(value):
        raise ParquetOpsError('INVALID_ARGUMENT', f"{field} 非法（需匹配 ^[a-z0-9_]+$，长度≤128）: {value!r}")
    return value


def parse_date(value: str) -> date:
    try:
        if not DATE_RE.match(value):
            raise ValueError(value)
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ParquetOpsError('INVALID_ARGUMENT', f"etl_date 非法（需 YYYY-MM-DD）: {value!r}")


class ParquetOpsService:
    """淘沙侧 Parquet 存储操作；store 可注入（测试用），默认构造 DuckdbParquetStore"""

    def __init__(self, store=None):
        if store is None:
            from utils.config import settings
            from .duckdb_parquet_store import DuckdbParquetStore

            mode = getattr(settings, 'fraudhunter_duck_compute_mode', 'local')
            if mode not in ('local', 'remote'):
                raise ParquetOpsError(
                    'NOT_CONFIGURED', f"淘沙后端 duck_compute.mode 必须为 local/remote，当前: {mode}",
                )
            store = DuckdbParquetStore()
        self.store = store
        self.storage_path = Path(store._storage_path).resolve()

    # ------------------------------------------------------------------
    # 路径与锁
    # ------------------------------------------------------------------
    def _version_dir(self, version_dir_name: str) -> Path:
        path = (self.storage_path / validate_name(version_dir_name, 'version_dir_name')).resolve()
        if path.parent != self.storage_path:
            raise ParquetOpsError('INVALID_ARGUMENT', f"版本目录越界: {version_dir_name!r}")
        return path

    @staticmethod
    def _date_dir(version_dir: Path, etl_date: date) -> Path:
        return version_dir / f"etl_date={etl_date.strftime('%Y-%m-%d')}"

    @contextmanager
    def _target_lock(self, version_dir_name: str, etl_date: date):
        lock_dir = self.storage_path / '.locks'
        lock_dir.mkdir(parents=True, exist_ok=True)
        lock_path = lock_dir / f"{version_dir_name}__{etl_date.strftime('%Y%m%d')}.lock"
        fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o644)
        try:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ParquetOpsError(
                    'BUSY', f"目标正在被另一请求写入: {version_dir_name} {etl_date}",
                )
            yield
        finally:
            try:
                fcntl.flock(fd, fcntl.LOCK_UN)
            finally:
                os.close(fd)

    def _translate(self, exc: Exception):
        """把存储层异常翻译为接口错误码（未知异常原样抛出 → 500）"""
        from .duckdb_parquet_store import ReconcileError, TargetUniverseChangedError

        if isinstance(exc, TargetUniverseChangedError):
            return ParquetOpsError('TARGET_UNIVERSE_CHANGED', str(exc))
        if isinstance(exc, ReconcileError):
            return ParquetOpsError('RECONCILE_FAILED', str(exc))
        return None

    # ------------------------------------------------------------------
    # 动作
    # ------------------------------------------------------------------
    def probe(self, version_dir_name: str, etl_date: date) -> dict:
        version_dir = self._version_dir(version_dir_name)
        result = self.store.probe_parquet(str(version_dir), etl_date)
        result['version_dir'] = str(version_dir)
        return result

    def pull(self, source_pg_table: str, source_kind: str, version_dir_name: str,
             etl_date: date, expected_rows: Optional[int] = None) -> dict:
        validate_name(source_pg_table, 'source_pg_table')
        if source_kind not in ('staging', 'partition'):
            raise ParquetOpsError('INVALID_ARGUMENT', f"source_kind 非法: {source_kind!r}（staging/partition）")
        if expected_rows is not None and expected_rows < 0:
            raise ParquetOpsError('INVALID_ARGUMENT', f"expected_rows 非法: {expected_rows}")
        version_dir = self._version_dir(version_dir_name)
        final_dir = self._date_dir(version_dir, etl_date)

        with self._target_lock(version_dir_name, etl_date):
            try:
                if source_kind == 'staging':
                    size_bytes = self.store.land_staging_to_parquet(
                        source_pg_table, final_dir, expected_rows,
                    )
                    rows, column_count = expected_rows, None
                else:
                    rows, column_count, size_bytes = self.store.pull_pg_partition_to_parquet(
                        source_pg_table, etl_date, final_dir, expected_rows=expected_rows,
                    )
            except Exception as e:
                translated = self._translate(e)
                if translated:
                    raise translated from e
                raise
        logger.info(
            f"[内部存储接口] pull 完成: source={source_kind}:{source_pg_table}, "
            f"dir={final_dir}, rows={rows}, size={size_bytes}"
        )
        return {
            'rows': rows, 'column_count': column_count, 'size_bytes': int(size_bytes or 0),
            'final_dir': str(final_dir), 'version_dir': str(version_dir),
        }

    def merge(self, base_version_dir_name: str, dest_version_dir_name: str, etl_date: date,
              delta_table: Optional[str], static_cols: list, inc_cols: list) -> dict:
        base_dir = self._version_dir(base_version_dir_name)
        dest_dir = self._version_dir(dest_version_dir_name)
        if delta_table is not None:
            validate_name(delta_table, 'delta_table')
        for col in list(static_cols) + list(inc_cols):
            validate_name(col, 'column')
        if not base_dir.is_dir():
            raise ParquetOpsError('NOT_FOUND', f"增量基准目录不存在: {base_dir}")

        with self._target_lock(dest_version_dir_name, etl_date):
            try:
                rows = self.store.merge_delta_insert_select(
                    dest_table=dest_version_dir_name,
                    base_table=str(base_dir),
                    delta_table=delta_table,
                    target_metadata={},
                    static_cols=list(static_cols),
                    inc_cols=list(inc_cols),
                    etl_date=etl_date.isoformat(),
                )
            except Exception as e:
                translated = self._translate(e)
                if translated:
                    raise translated from e
                raise
        final_dir = self._date_dir(dest_dir, etl_date)
        size_bytes = sum(f.stat().st_size for f in final_dir.glob('*.parquet')) if final_dir.is_dir() else 0
        logger.info(
            f"[内部存储接口] merge 完成: base={base_version_dir_name}, dir={final_dir}, rows={rows}"
        )
        return {
            'rows': int(rows), 'size_bytes': int(size_bytes),
            'final_dir': str(final_dir), 'version_dir': str(dest_dir),
        }

    def cleanup(self, version_dir_name: str, etl_date: date) -> dict:
        version_dir = self._version_dir(version_dir_name)
        tmp_dir = self._date_dir(version_dir, etl_date)
        tmp_dir = tmp_dir.with_name(tmp_dir.name + '.tmp')
        with self._target_lock(version_dir_name, etl_date):
            existed = tmp_dir.exists()
            if existed:
                if getattr(self.store, '_duck_compute_mode', lambda: 'local')() == 'remote':
                    # 容器写入的文件属主可能不同，经网关在容器内删除
                    self.store._remote().remote_write_cleanup(tmp_dir.as_posix())
                else:
                    shutil.rmtree(tmp_dir, ignore_errors=True)
        return {'removed': existed, 'tmp_dir': str(tmp_dir)}
