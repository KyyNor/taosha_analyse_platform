"""
离线宽表互转服务（PG离线表 ↔ DuckDB Parquet 按日期互转）

双存储方案阶段5（docs/fraudhunter_offline_dual_store_plan.md）：
- pg2duckdb: PG 正式表指定日期 → Parquet（复用 DuckdbParquetStore 拉取原语，
  与同步路径同源：COPY列式直转 → 对账 → 原子落盘）；
- duckdb2pg: Parquet 指定日期 → PG 正式表（应急回退通道）；
- 元数据规则：对账通过后才改写/新增快照记录（storage_backend + parquet_file_path）；
- 幂等：目标已存在则跳过（--overwrite 除外）；
- --keep-source 默认保留源侧数据，清理交给现有分区清理延迟处理。
"""

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from models.db_base import get_db_session
from models.fraudhunter.wide_table import (
    FraudHunterWideTableVersion,
    FraudHunterWideTableSnapshot,
)
from utils.logger import logger
from .store.duckdb_parquet_store import DuckdbParquetStore
from .store.pg_store import PgWideTableStore


class WideTableTransferService:
    """离线宽表存储互转服务"""

    def __init__(self) -> None:
        self._duck_store = DuckdbParquetStore()
        self._pg_store = PgWideTableStore()

    def transfer(
        self,
        wide_table_name: str,
        version_hash: str,
        etl_dates: List[date],
        direction: str,
        keep_source: bool = True,
        overwrite: bool = False,
    ) -> List[Dict]:
        """按日期批量互转（CLI入口）

        Returns:
            每个日期的结果列表：
            {"etl_date", "status": transferred/skipped/failed, "detail", ...}
        """
        if direction not in ('pg2duckdb', 'duckdb2pg'):
            raise ValueError(f"不支持的互转方向: {direction}")

        results = []
        for etl_date in etl_dates:
            try:
                if direction == 'pg2duckdb':
                    results.append(
                        self._transfer_pg_to_duckdb(
                            wide_table_name, version_hash, etl_date,
                            overwrite=overwrite,
                        )
                    )
                else:
                    results.append(
                        self._transfer_duckdb_to_pg(
                            wide_table_name, version_hash, etl_date,
                            keep_source=keep_source,
                            overwrite=overwrite,
                        )
                    )
            except Exception as e:
                logger.error(
                    f"[互转失败] {direction} {wide_table_name} {version_hash[:8]} "
                    f"{etl_date}: {e}",
                    exc_info=True,
                )
                results.append({
                    "etl_date": str(etl_date),
                    "status": "failed",
                    "detail": str(e)[:500],
                })
        return results

    # ------------------------------------------------------------------
    # pg → duckdb
    # ------------------------------------------------------------------

    def _transfer_pg_to_duckdb(
        self,
        wide_table_name: str,
        version_hash: str,
        etl_date: date,
        overwrite: bool,
    ) -> Dict:
        pg_table = f"{wide_table_name}_{version_hash[:8]}"
        duck_version_dir = self._duck_store.version_dir(pg_table)
        date_dir = self._duck_store.date_dir(pg_table, etl_date)

        with get_db_session() as db:
            source_snapshot = self._find_snapshot(
                db, wide_table_name, version_hash, etl_date, 'postgresql'
            )
            if not source_snapshot:
                return {
                    "etl_date": str(etl_date),
                    "status": "skipped",
                    "detail": f"未找到postgresql侧ready快照 ({wide_table_name} {version_hash[:8]} {etl_date})",
                }

            # 幂等：目标日期目录已存在则跳过
            if date_dir.exists() and not overwrite:
                return {
                    "etl_date": str(etl_date),
                    "status": "skipped",
                    "detail": f"目标目录已存在: {date_dir}（--overwrite 可重转）",
                }

            target_snapshot = self._upsert_generating_snapshot(
                db, wide_table_name, version_hash, etl_date, 'duckdb'
            )

        try:
            row_count, column_count, size_bytes = (
                self._duck_store.pull_pg_partition_to_parquet(pg_table, etl_date, date_dir)
            )
            with get_db_session() as db:
                self._mark_snapshot_ready(
                    db, target_snapshot,
                    parquet_file_path=str(duck_version_dir.resolve()),
                    row_count=row_count,
                    column_count=column_count,
                    file_size_bytes=size_bytes,
                )
            # keep_source 默认True：PG表/源快照保留，由现有分区清理延迟处理
            return {
                "etl_date": str(etl_date),
                "status": "transferred",
                "row_count": row_count,
                "column_count": column_count,
                "file_size_bytes": size_bytes,
                "parquet_dir": str(date_dir),
            }
        except Exception as e:
            with get_db_session() as db:
                self._mark_snapshot_failed(db, target_snapshot, str(e))
            raise

    # ------------------------------------------------------------------
    # duckdb → pg（应急回退通道）
    # ------------------------------------------------------------------

    def _transfer_duckdb_to_pg(
        self,
        wide_table_name: str,
        version_hash: str,
        etl_date: date,
        keep_source: bool,
        overwrite: bool,
    ) -> Dict:
        pg_table = f"{wide_table_name}_{version_hash[:8]}"
        duck_version_dir = self._duck_store.version_dir(pg_table)
        date_dir = self._duck_store.date_dir(pg_table, etl_date)

        with get_db_session() as db:
            source_snapshot = self._find_snapshot(
                db, wide_table_name, version_hash, etl_date, 'duckdb'
            )
            if not source_snapshot:
                return {
                    "etl_date": str(etl_date),
                    "status": "skipped",
                    "detail": f"未找到duckdb侧ready快照 ({wide_table_name} {version_hash[:8]} {etl_date})",
                }
            if not date_dir.exists():
                return {
                    "etl_date": str(etl_date),
                    "status": "skipped",
                    "detail": f"Parquet日期目录不存在: {date_dir}",
                }

            # 幂等：目标PG分区已有数据则跳过
            from utils.analyze_db_utils import AnalyzeDBPartitionManager

            partition_name = f"{pg_table}_{etl_date.strftime('%Y%m%d')}"
            if not overwrite and AnalyzeDBPartitionManager.table_exists(partition_name):
                existing_rows = AnalyzeDBPartitionManager.count_partition_rows(partition_name)
                if existing_rows and existing_rows > 0:
                    return {
                        "etl_date": str(etl_date),
                        "status": "skipped",
                        "detail": f"目标PG分区已有 {existing_rows} 行（--overwrite 可重转）",
                    }

            indicator_metadata = self._get_version_metadata(db, version_hash)
            target_snapshot = self._upsert_generating_snapshot(
                db, wide_table_name, version_hash, etl_date, 'postgresql'
            )

        try:
            row_count = self._duck_store.push_parquet_to_pg(
                duck_version_dir, etl_date, pg_table, indicator_metadata
            )
            with get_db_session() as db:
                self._mark_snapshot_ready(
                    db, target_snapshot,
                    parquet_file_path=pg_table,
                    row_count=row_count,
                    column_count=None,
                    file_size_bytes=None,
                )
            # keep_source 默认True：Parquet目录与duckdb快照保留
            return {
                "etl_date": str(etl_date),
                "status": "transferred",
                "row_count": row_count,
                "pg_table": pg_table,
            }
        except Exception as e:
            with get_db_session() as db:
                self._mark_snapshot_failed(db, target_snapshot, str(e))
            raise

    # ------------------------------------------------------------------
    # 快照元数据
    # ------------------------------------------------------------------

    @staticmethod
    def _find_snapshot(
        db,
        wide_table_name: str,
        version_hash: str,
        etl_date: date,
        storage_backend: str,
    ) -> Optional[FraudHunterWideTableSnapshot]:
        from sqlalchemy import and_

        return db.query(FraudHunterWideTableSnapshot).filter(and_(
            FraudHunterWideTableSnapshot.wide_table_name == wide_table_name,
            FraudHunterWideTableSnapshot.version_hash == version_hash,
            FraudHunterWideTableSnapshot.etl_date == etl_date,
            FraudHunterWideTableSnapshot.storage_backend == storage_backend,
            FraudHunterWideTableSnapshot.status == 'ready',
        )).first()

    @staticmethod
    def _upsert_generating_snapshot(
        db,
        wide_table_name: str,
        version_hash: str,
        etl_date: date,
        storage_backend: str,
    ) -> int:
        from sqlalchemy import and_

        snapshot = db.query(FraudHunterWideTableSnapshot).filter(and_(
            FraudHunterWideTableSnapshot.wide_table_name == wide_table_name,
            FraudHunterWideTableSnapshot.version_hash == version_hash,
            FraudHunterWideTableSnapshot.etl_date == etl_date,
            FraudHunterWideTableSnapshot.storage_backend == storage_backend,
        )).first()

        if snapshot:
            snapshot.status = 'generating'
            snapshot.error_message = None
            db.commit()
            return snapshot.id

        new_snapshot = FraudHunterWideTableSnapshot(
            wide_table_name=wide_table_name,
            etl_date=etl_date,
            version_hash=version_hash,
            parquet_file_path="",
            storage_backend=storage_backend,
            status='generating',
        )
        db.add(new_snapshot)
        db.commit()
        db.refresh(new_snapshot)
        return new_snapshot.id

    @staticmethod
    def _mark_snapshot_ready(
        db,
        snapshot_id: int,
        parquet_file_path: str,
        row_count: int,
        column_count: Optional[int],
        file_size_bytes: Optional[int],
    ) -> None:
        snapshot = db.query(FraudHunterWideTableSnapshot).get(snapshot_id)
        if not snapshot:
            return
        snapshot.status = 'ready'
        snapshot.parquet_file_path = parquet_file_path
        snapshot.row_count = row_count
        if column_count is not None:
            snapshot.column_count = column_count
        if file_size_bytes is not None:
            snapshot.file_size_bytes = file_size_bytes
        snapshot.generation_time = datetime.now()
        snapshot.error_message = None
        db.commit()

    @staticmethod
    def _mark_snapshot_failed(db, snapshot_id: int, error: str) -> None:
        snapshot = db.query(FraudHunterWideTableSnapshot).get(snapshot_id)
        if not snapshot:
            return
        snapshot.status = 'failed'
        snapshot.error_message = error[:1000]
        db.commit()

    @staticmethod
    def _get_version_metadata(db, version_hash: str) -> dict:
        version = db.query(FraudHunterWideTableVersion).filter(
            FraudHunterWideTableVersion.version_hash == version_hash
        ).first()
        if not version:
            raise ValueError(f"版本记录不存在: {version_hash[:8]}")
        return version.indicator_metadata or {}


def resolve_etl_dates(dates: Optional[List[str]], backfill: Optional[int]) -> List[date]:
    """解析 CLI 日期参数：--dates 列表 或 --backfill N（最近N天，含今日）"""
    if dates:
        return [datetime.strptime(d, '%Y-%m-%d').date() for d in dates]
    if backfill and backfill > 0:
        today = date.today()
        return [today - timedelta(days=i) for i in range(backfill)]
    raise ValueError("必须指定 --dates 或 --backfill 之一")
