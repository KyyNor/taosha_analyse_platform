"""
Parquet 版本目录清理定时任务（双存储方案阶段6）

清理策略（引用计数，防止误删被多快照复用的目录）：
1. 统计所有 duckdb 快照引用的版本目录（generating/ready 状态均计入，
   避免与同步中的任务竞态）；
2. 未被引用且超过宽限期的版本目录 → 删除（零拷贝复用/版本退役后自然释放）；
3. 残留的 .tmp/.trash 中间目录超过宽限期 → 删除（同步中断遗留）。
   中间目录既可能在 storage_path 顶层（历史布局），也可能在版本目录下一层
   （{version_dir}/{etl_date}.tmp），两处都要扫。

版本退役链路：PG侧 _cleanup_history_wide_table_versions 删除版本记录时
ORM 级联删除其快照 → 目录引用归零 → 本任务延迟物理删除。
"""

import fcntl
import os
import re
import shutil
import time
from contextlib import contextmanager, ExitStack
from pathlib import Path

from models.db_base import get_db_session
from models.fraudhunter.wide_table import FraudHunterWideTableSnapshot
from utils.config import settings
from utils.logger import logger

INTERMEDIATE_SUFFIXES = ('.tmp', '.trash')


def _referenced_parquet_dirs() -> set:
    """统计被 duckdb 快照引用的版本目录绝对路径集合"""
    with get_db_session() as db:
        snapshots = db.query(FraudHunterWideTableSnapshot).filter(
            FraudHunterWideTableSnapshot.storage_backend == 'duckdb',
            FraudHunterWideTableSnapshot.status.in_(['generating', 'ready']),
        ).all()
        return {
            Path(s.parquet_file_path).resolve().as_posix()
            for s in snapshots
            if s.parquet_file_path
        }


def _dir_age_hours(path: Path) -> float:
    """目录最近修改时间距今的小时数"""
    latest = max(path.stat().st_mtime, max(
        (f.stat().st_mtime for f in path.rglob("*")), default=0,
    ))
    return (time.time() - latest) / 3600


@contextmanager
def _version_cleanup_lock(storage_path: Path, version_dir: Path):
    """持有已有写入锁及日期目录对应锁直至清理结束；忙碌时跳过整个版本。

    与 ParquetOpsService._target_lock 共用锁文件，禁止删除/重建锁文件，
    否则另一个 worker 可能锁住不同 inode。
    """
    lock_dir = storage_path / '.locks'
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_paths = set(lock_dir.glob(f'{version_dir.name}__*.lock'))
    for child in version_dir.iterdir():
        match = re.fullmatch(r'etl_date=(\d{4})-(\d{2})-(\d{2})(?:\.(?:tmp|trash))?', child.name)
        if match:
            lock_paths.add(lock_dir / f"{version_dir.name}__{''.join(match.groups())}.lock")
    with ExitStack() as stack:
        for lock_path in sorted(lock_paths):
            fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o644)
            stack.callback(os.close, fd)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                yield False
                return
        yield True


def _is_intermediate_dir(path: Path) -> bool:
    return path.is_dir() and path.name.endswith(INTERMEDIATE_SUFFIXES)


def _remove_dir(path: Path, compute_mode: str) -> None:
    """删除目录：remote 模式下容器写入的文件属主可能不同，优先经网关在容器内删除"""
    if compute_mode == 'remote':
        try:
            from services.fraudhunter.wide_table_service.store import remote_session
            remote_session.remote_write_cleanup(path.as_posix())
            return
        except Exception as e:
            logger.warning(f"经网关删除失败，回退本地删除: {path}: {e}")
    shutil.rmtree(path, ignore_errors=True)


async def parquet_cleanup_job():
    """Parquet版本目录引用计数清理任务"""
    try:
        # 纯 PG 模式 no-op（Issue #10）：未启用 DuckDB 存储时不访问/修改
        # Parquet 目录（防止历史测试/手工文件残留导致误清理），任务本体兜底，
        # 调度侧（main.py）也按 offline_store 条件注册
        offline_store = getattr(
            settings, 'fraudhunter_wide_table_offline_store', 'postgresql',
        )
        if offline_store not in ('duckdb', 'both'):
            logger.debug(
                f"offline_store={offline_store}，Parquet清理任务 no-op（未启用DuckDB存储）"
            )
            return

        storage_path = Path(settings.fraudhunter_wide_table_duckdb_storage_path)
        grace_hours = getattr(
            settings,
            'fraudhunter_wide_table_duckdb_parquet_cleanup_grace_hours',
            48,
        )
        compute_mode = getattr(settings, 'fraudhunter_duck_compute_mode', 'local')
        if not storage_path.is_dir():
            logger.debug(f"Parquet存储目录不存在，跳过清理: {storage_path}")
            return

        referenced = _referenced_parquet_dirs()
        deleted_dirs = 0
        deleted_tmp = 0

        for entry in storage_path.iterdir():
            if not entry.is_dir():
                continue
            # .locks 等工作目录不属于数据目录，禁止按引用计数清理
            if entry.name.startswith('.'):
                continue

            # 顶层中间目录（历史布局/落盘中断）
            if _is_intermediate_dir(entry):
                if _dir_age_hours(entry) > grace_hours:
                    _remove_dir(entry, compute_mode)
                    deleted_tmp += 1
                    logger.info(f"清理残留中间目录: {entry}")
                continue

            with _version_cleanup_lock(storage_path, entry) as acquired:
                if not acquired:
                    logger.debug(f"版本目录正在写入，跳过清理: {entry}")
                    continue
                # 版本目录内的中间目录（同步中断现场）：仅扫一层，布局为
                # {version_dir}/{etl_date=YYYY-MM-DD}.tmp
                try:
                    children = list(entry.iterdir())
                except OSError as e:
                    logger.warning(f"无法列出版本目录，跳过中间目录清理: {entry}: {e}")
                    children = []
                for child in children:
                    if _is_intermediate_dir(child) and _dir_age_hours(child) > grace_hours:
                        _remove_dir(child, compute_mode)
                        deleted_tmp += 1
                        logger.info(f"清理残留中间目录: {child}")

                # 正式版本目录：引用计数为0且过宽限期才删
                resolved = entry.resolve().as_posix()
                if resolved in referenced:
                    continue
                if _dir_age_hours(entry) > grace_hours:
                    _remove_dir(entry, compute_mode)
                    deleted_dirs += 1
                    logger.info(f"清理无引用Parquet版本目录: {entry}")

        logger.info(
            f"Parquet目录清理完成: 删除版本目录{deleted_dirs}个, "
            f"中间目录{deleted_tmp}个 (引用中{len(referenced)}, 宽限期{grace_hours}h)"
        )

    except Exception as e:
        logger.error(f"Parquet目录清理失败: {e}", exc_info=True)


def main():
    import asyncio

    asyncio.run(parquet_cleanup_job())


if __name__ == '__main__':
    main()
