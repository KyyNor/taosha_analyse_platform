"""
PG 表分区导出 Parquet CLI（自双存储方案移植的单一能力，不依赖宽表快照元数据）

能力来源：feature/offline-dual-store 分支 DuckdbParquetStore.pull_pg_partition_to_parquet
（双存储方案阶段5 pg2duckdb 拉取原语）。本模块将其剥离为自包含工具：
给定 PG 表名与日期分区，经 DuckDB ATTACH PG (READ_ONLY) COPY 列式直转 Parquet，
导出前后做行数 + 内容 checksum 对账，tmp 目录原子落盘；不改动 PG 源数据，
不写任何宽表快照/版本元数据，适合人工排查、数据外送等场景。

目录布局（沿用存储侧 hive 分区约定）：
    {output_root}/{table}/etl_date=YYYY-MM-DD/part-00000.parquet

用法（backend 目录下执行）：
    # 指定日期导出（默认目录读配置 fraudhunter.pg_partition_export.output_dir）
    uv run python -m scripts.pg_partition_export --table cust_wide_table_a1b2c3d4 \
        --dates 2026-09-01 2026-09-02

    # 回溯最近7天，导出到指定目录并覆盖已存在分区
    uv run python -m scripts.pg_partition_export --table cust_wide_table_a1b2c3d4 \
        --backfill 7 --output-dir /data/export --overwrite
"""

import sys
import argparse
import os
import shutil
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

from utils.config import settings
from utils.logger import logger

# Parquet 内单文件命名（与双存储方案一致，不做多文件合并）
PARQUET_FILE_PATTERN = "part-*.parquet"


class PgPartitionExporter:
    """PG 正式表按日期分区 → Parquet 导出器（COPY 列式直转 + 对账 + 原子落盘）"""

    def __init__(self, compression: Optional[str] = None) -> None:
        self._compression = compression or settings.fraudhunter_pg_partition_export_compression

    def export_partition(
        self,
        pg_table: str,
        etl_date: date,
        dest_dir: Path,
    ) -> Tuple[int, int, int]:
        """PG 表指定日期分区 → Parquet 目录

        Returns:
            (row_count, column_count, file_size_bytes)
        """
        date_str = etl_date.strftime('%Y-%m-%d')
        source_relation = (
            f"(SELECT * EXCLUDE (created_at) FROM pg_src.public.{pg_table} "
            f"WHERE etl_date = DATE '{date_str}')"
        )

        tmp_dir = self._prepare_tmp_dir(dest_dir)

        conn = self._attach_pg()
        try:
            copy_sql = self._build_partition_copy_sql(pg_table, etl_date, tmp_dir)
            logger.debug(f"[pg导出] COPY SQL: {copy_sql}")
            conn.execute(copy_sql)

            # 对账：PG分区行数+内容 vs parquet行数+内容（同一DuckDB会话内完成）
            source_rows = conn.execute(
                f"SELECT count(*) FROM {source_relation}"
            ).fetchone()[0]
            self._reconcile(conn, source_relation, self._parquet_relation(tmp_dir), source_rows)
            parquet_cols = [
                row[0] for row in conn.execute(
                    f"DESCRIBE SELECT * FROM {self._parquet_relation(tmp_dir)}"
                ).fetchall()
            ]
        finally:
            try:
                conn.execute("DETACH pg_src")
            except Exception:
                pass
            conn.close()

        self._atomic_landing(tmp_dir, dest_dir)
        size_bytes = sum(f.stat().st_size for f in dest_dir.glob(PARQUET_FILE_PATTERN))
        logger.info(
            f"[pg导出] 完成: {pg_table} {date_str} → {dest_dir}, "
            f"{source_rows}行 {len(parquet_cols)}列 {size_bytes}B"
        )
        return (int(source_rows), len(parquet_cols), size_bytes)

    # ------------------------------------------------------------------
    # DuckDB 连接与 SQL 构建（独立方法便于单测）
    # ------------------------------------------------------------------

    def _attach_pg(self):
        """建立 DuckDB 连接并 ATTACH PG（READ_ONLY）"""
        import duckdb

        pg = settings.fraudhunter_analyze_db['postgresql']
        conn_string = (
            f"dbname={pg['database']} host={pg['host']} port={pg['port']} "
            f"user={pg['user']} password={pg['password']}"
        )
        escaped = conn_string.replace("\\", "\\\\").replace("'", "\\'")

        conn = duckdb.connect()
        try:
            conn.execute("LOAD postgres;")
            conn.execute(f"ATTACH '{escaped}' AS pg_src (TYPE POSTGRES, READ_ONLY);")
        except Exception:
            conn.close()
            raise
        return conn

    def _build_partition_copy_sql(self, pg_table: str, etl_date: date, tmp_dir: Path) -> str:
        """PG 正式表按日期过滤 COPY → Parquet（分区裁剪下推到PG，排除 created_at 审计列）"""
        target = (tmp_dir / "part-00000.parquet").as_posix()
        return (
            f"COPY (SELECT * EXCLUDE (created_at) FROM pg_src.public.{pg_table} "
            f"WHERE etl_date = DATE '{etl_date.strftime('%Y-%m-%d')}') "
            f"TO '{target}' (FORMAT PARQUET, COMPRESSION {self._compression})"
        )

    @staticmethod
    def _build_checksum_sql(relation: str, columns: List[str]) -> str:
        """构建行数 + 顺序无关内容校验和（sum(hash(行拼接))）"""
        joined = ", ".join(f"{col}::VARCHAR" for col in columns)
        return f"SELECT count(*), sum(hash(concat_ws('|', {joined}))) FROM {relation}"

    def _reconcile(self, conn, source_relation: str, parquet_relation: str,
                   source_rows: int) -> None:
        """对账：列集合 + 行数 + 内容checksum，不一致即抛异常（不落盘）"""
        parquet_cols = [
            row[0] for row in conn.execute(
                f"DESCRIBE SELECT * FROM {parquet_relation}"
            ).fetchall()
        ]
        source_cols = [
            row[0] for row in conn.execute(
                f"DESCRIBE SELECT * FROM {source_relation}"
            ).fetchall()
        ]
        parquet_n, parquet_hash = conn.execute(
            self._build_checksum_sql(parquet_relation, parquet_cols)
        ).fetchone()
        source_n, source_hash = conn.execute(
            self._build_checksum_sql(source_relation, parquet_cols)
        ).fetchone()

        # 列集合一致（源表允许有多出的 created_at 审计列）
        extra = [c for c in parquet_cols if c not in source_cols]
        if extra:
            raise RuntimeError(f"[pg导出] 对账失败: parquet多出源表不存在的列: {extra}")
        if source_rows != source_n:
            raise RuntimeError(
                f"[pg导出] 对账失败: 分区行数({source_rows}) != 源表行数({source_n})"
            )
        if source_n != parquet_n:
            raise RuntimeError(
                f"[pg导出] 对账失败: 源表行数({source_n}) != parquet行数({parquet_n})"
            )
        if source_hash != parquet_hash:
            raise RuntimeError(
                f"[pg导出] 对账失败: 内容校验和不一致 "
                f"(source={source_hash}, parquet={parquet_hash})"
            )
        logger.info(f"[pg导出] 对账通过: 行数={parquet_n}, checksum={parquet_hash}")

    @staticmethod
    def _parquet_relation(tmp_dir: Path) -> str:
        glob = (tmp_dir / PARQUET_FILE_PATTERN).as_posix()
        return f"read_parquet('{glob}')"

    @staticmethod
    def _prepare_tmp_dir(final_dir: Path) -> Path:
        """准备 COPY 落盘的临时目录（DuckDB COPY 不会自动建父目录）

        幂等——清掉上次失败残留的 tmp 目录后重建，避免旧 part 文件混入本次对账。
        """
        tmp_dir = final_dir.with_name(final_dir.name + ".tmp")
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
        tmp_dir.mkdir(parents=True)
        return tmp_dir

    @staticmethod
    def _atomic_landing(tmp_dir: Path, final_dir: Path) -> None:
        """临时目录原子落盘：tmp → final（若 final 已存在先挪走再删）"""
        if not tmp_dir.exists():
            raise RuntimeError(f"[pg导出] 临时目录不存在，无法落盘: {tmp_dir}")

        final_dir.parent.mkdir(parents=True, exist_ok=True)
        trash = final_dir.with_name(final_dir.name + ".trash")
        if trash.exists():
            shutil.rmtree(trash)

        if final_dir.exists():
            os.rename(final_dir, trash)
        try:
            os.rename(tmp_dir, final_dir)
        except Exception:
            # 回滚保护：恢复旧目录
            if trash.exists() and not final_dir.exists():
                os.rename(trash, final_dir)
            raise
        if trash.exists():
            shutil.rmtree(trash)


def resolve_etl_dates(dates: Optional[List[str]], backfill: Optional[int]) -> List[date]:
    """解析 CLI 日期参数：--dates 列表 或 --backfill N（最近N天，含今日）"""
    if dates:
        return [datetime.strptime(d, '%Y-%m-%d').date() for d in dates]
    if backfill and backfill > 0:
        today = date.today()
        return [today - timedelta(days=i) for i in range(backfill)]
    raise ValueError("必须指定 --dates 或 --backfill 之一")


def build_dest_dir(output_root: Path, table: str, etl_date: date) -> Path:
    """导出目标目录：{output_root}/{table}/etl_date=YYYY-MM-DD"""
    return output_root / table / f"etl_date={etl_date.strftime('%Y-%m-%d')}"


def main():
    parser = argparse.ArgumentParser(
        description='PG 表指定日期分区导出为 Parquet 文件（对账+原子落盘，无元数据操作）',
    )
    parser.add_argument('--table', required=True,
                        help='PG 表名（如 cust_wide_table_a1b2c3d4）')
    parser.add_argument('--dates', nargs='+',
                        help='日期列表 YYYY-MM-DD（与 --backfill 二选一）')
    parser.add_argument('--backfill', type=int,
                        help='回溯天数（最近N天含今日，与 --dates 二选一）')
    parser.add_argument('--output-dir',
                        help='输出根目录（默认取配置 fraudhunter.pg_partition_export.output_dir）')
    parser.add_argument('--overwrite', action='store_true',
                        help='目标日期目录已存在时重导（默认幂等跳过）')

    args = parser.parse_args()

    etl_dates = resolve_etl_dates(args.dates, args.backfill)
    output_root = Path(
        args.output_dir or settings.fraudhunter_pg_partition_export_output_dir
    )

    logger.info(
        f"[pg导出] 开始: table={args.table} 共{len(etl_dates)}天 "
        f"output_root={output_root} overwrite={args.overwrite}"
    )

    exporter = PgPartitionExporter()
    succeeded, skipped, failed = 0, 0, 0
    for etl_date in etl_dates:
        dest_dir = build_dest_dir(output_root, args.table, etl_date)
        if dest_dir.exists() and not args.overwrite:
            skipped += 1
            logger.info(f"[pg导出] {etl_date} skipped: 目标目录已存在 {dest_dir}")
            continue
        try:
            exporter.export_partition(args.table, etl_date, dest_dir)
            succeeded += 1
        except Exception as e:
            failed += 1
            logger.error(f"[pg导出] {etl_date} failed: {e}", exc_info=True)

    logger.info(
        f"[pg导出] 完成: table={args.table}, 成功{succeeded} 跳过{skipped} 失败{failed}"
    )
    if failed:
        sys.exit(1)


if __name__ == '__main__':
    main()
