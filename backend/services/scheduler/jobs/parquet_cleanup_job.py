"""
Parquet 版本目录清理定时任务（双存储方案阶段6）

清理策略（引用计数，防止误删被多快照复用的目录）：
1. 统计所有 duckdb 快照引用的版本目录（generating/ready 状态均计入，
   避免与同步中的任务竞态）；
2. 未被引用且超过宽限期的版本目录 → 删除（零拷贝复用/版本退役后自然释放）；
3. 残留的 .tmp/.trash 中间目录超过宽限期 → 删除（同步中断遗留）。

版本退役链路：PG侧 _cleanup_history_wide_table_versions 删除版本记录时
ORM 级联删除其快照 → 目录引用归零 → 本任务延迟物理删除。
"""

import shutil
import time
from pathlib import Path

from models.db_base import get_db_session
from models.fraudhunter.wide_table import FraudHunterWideTableSnapshot
from utils.config import settings
from utils.logger import logger


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
    latest = max((f.stat().st_mtime for f in path.rglob("*") if f.is_file()), default=0)
    return (time.time() - latest) / 3600


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
        if not storage_path.is_dir():
            logger.debug(f"Parquet存储目录不存在，跳过清理: {storage_path}")
            return

        referenced = _referenced_parquet_dirs()
        deleted_dirs = 0
        deleted_tmp = 0

        for entry in storage_path.iterdir():
            if not entry.is_dir():
                continue

            # 中间目录（同步中断遗留）
            if entry.name.endswith(('.tmp', '.trash')):
                if _dir_age_hours(entry) > grace_hours:
                    shutil.rmtree(entry, ignore_errors=True)
                    deleted_tmp += 1
                    logger.info(f"清理残留中间目录: {entry}")
                continue

            # 正式版本目录：引用计数为0且过宽限期才删
            resolved = entry.resolve().as_posix()
            if resolved in referenced:
                continue
            if _dir_age_hours(entry) > grace_hours:
                shutil.rmtree(entry, ignore_errors=True)
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
