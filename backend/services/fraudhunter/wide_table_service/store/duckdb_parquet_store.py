"""
DuckDB Parquet 离线宽表存储实现（双存储方案阶段3）

同步链路（docs/fraudhunter_offline_dual_store_plan.md §2.1）：

    Spark/Hive 明细长表
      → PIVOT → executor JDBC 写 PG staging 表（UNLOGGED，仅传输管道）
      → DuckDB ATTACH PG + COPY 拉成 Parquet（列式直转，单条SQL）
      → 三方对账（Spark行数 vs staging行数 vs parquet行数+checksum）
      → 原子 rename 落盘
      → DROP staging

与 PG 正式离线表的严格边界（§2.2）：
- UNLOGGED 只用于本类的 _staging_ 前缀中转表；
- 正式离线表、实时表、PG 模式 _delta_/_incr_ 辅助表一律 LOGGED，不经本类。

目录规范（§2.3）：
    {storage_path}/{wide_table_name}_{version_hash[:8]}/etl_date=YYYY-MM-DD/part-*.parquet
"""

import os
import shutil
from datetime import date
from pathlib import Path
from typing import List, Tuple

from utils.analyze_db_utils import AnalyzeDBPartitionManager
from utils.config import settings
from utils.logger import logger
from .base import WideTableStore
from .pg_store import PgWideTableStore

# Parquet 内单文件命名（多文件原生扫描，不做单文件合并）
PARQUET_FILE_PATTERN = "part-*.parquet"


class DuckdbParquetStore(WideTableStore):
    """DuckDB Parquet 离线宽表存储（staging 中转全量 + 本地增量列改写）"""

    name = 'duckdb'
    supports_delta_insert_select = True

    def __init__(self) -> None:
        self._storage_path = Path(settings.fraudhunter_wide_table_duckdb_storage_path)
        self._compression = settings.fraudhunter_wide_table_duckdb_compression
        # 复用已验证的 PySpark/JDBC → PG 执行器（写 staging）
        self._pg_writer = PgWideTableStore()

    # ------------------------------------------------------------------
    # 路径与表名规范
    # ------------------------------------------------------------------

    def version_dir(self, table_name: str) -> Path:
        """版本目录: {storage_path}/{wide_table_name}_{version_hash[:8]}"""
        return self._storage_path / table_name

    def date_dir(self, table_name: str, etl_date: date) -> Path:
        """日期目录: {version_dir}/etl_date=YYYY-MM-DD"""
        return self.version_dir(table_name) / f"etl_date={etl_date.strftime('%Y-%m-%d')}"

    @staticmethod
    def staging_table_name(table_name: str, etl_date: date) -> str:
        """staging 中转表名: _staging_{wide_table}_{vh8}_{yyyymmdd}"""
        return f"_staging_{table_name}_{etl_date.strftime('%Y%m%d')}"

    # ------------------------------------------------------------------
    # WideTableStore 接口
    # ------------------------------------------------------------------

    def ensure_table(
        self,
        table_name: str,
        indicator_metadata: dict,
        etl_date: date,
    ) -> None:
        """准备落盘目录与 UNLOGGED staging 中转表（幂等：重建 staging）"""
        self._storage_path.mkdir(parents=True, exist_ok=True)

        staging = self.staging_table_name(table_name, etl_date)
        AnalyzeDBPartitionManager.drop_table(staging)
        AnalyzeDBPartitionManager.create_heap_table(staging, indicator_metadata, unlogged=True)
        logger.info(f"已创建UNLOGGED staging中转表: {staging}")

    def create_heap_table(self, table_name: str, indicator_metadata: dict, **kwargs) -> None:
        """staging 辅助表一律 UNLOGGED（仅传输管道用途）"""
        AnalyzeDBPartitionManager.create_heap_table(table_name, indicator_metadata, unlogged=True)

    def drop_table(self, table_name: str) -> None:
        AnalyzeDBPartitionManager.drop_table(table_name)

    def write_pivot(
        self,
        sql: str,
        table_name: str,
        etl_date: date,
        refresh_sql: str | None = None,
    ) -> Tuple[int, int]:
        """全量写入：staging 中转 → DuckDB 拉 Parquet → 对账 → 原子落盘

        Returns:
            (row_count, column_count)
        """
        staging = self.staging_table_name(table_name, etl_date)
        final_dir = self.date_dir(table_name, etl_date)
        tmp_dir = final_dir.with_name(final_dir.name + ".tmp")

        # 1. executor 并行 JDBC 写 staging（数据不过应用服务器）
        spark_rows, column_count = self._pg_writer.write_pivot(
            sql, staging, etl_date, refresh_sql=refresh_sql
        )
        logger.info(
            f"[duckdb] staging写入完成: {staging}, {spark_rows}行, 开始DuckDB列式拉取"
        )

        # 2. DuckDB COPY staging → Parquet（临时目录）
        tmp_dir.mkdir(parents=True, exist_ok=True)

        conn = self._attach_pg()
        try:
            copy_sql = self._build_copy_sql(staging, tmp_dir)
            logger.debug(f"[duckdb] COPY SQL: {copy_sql}")
            conn.execute(copy_sql)

            # 3. 三方对账：Spark行数 vs staging行数 vs parquet行数 + 内容checksum
            # 失败抛异常，保留 tmp 目录与 staging 便于排障（staging 由 TTL 兜底清理）
            self._reconcile(conn, staging, tmp_dir, spark_rows)
        finally:
            try:
                conn.execute("DETACH pg_src")
            except Exception:
                pass
            conn.close()

        # 4. 原子落盘 + 释放 staging
        self._atomic_landing(tmp_dir, final_dir)
        AnalyzeDBPartitionManager.drop_table(staging)
        logger.info(f"[duckdb] Parquet落盘完成: {final_dir}")

        return (spark_rows, column_count)

    def write_pivot_to_pg(
        self,
        sql: str,
        table_name: str,
        etl_date: date,
        refresh_sql: str | None = None,
    ) -> Tuple[int, int]:
        """增量路径：PIVOT 结果直接写 PG delta 辅助表（不经 Parquet 中转）"""
        return self._pg_writer.write_pivot(sql, table_name, etl_date, refresh_sql=refresh_sql)

    def merge_delta_insert_select(
        self,
        dest_table: str,
        base_table: str,
        delta_table: str | None,
        target_metadata: dict,
        static_cols: list,
        inc_cols: list,
        etl_date: str,
    ) -> int:
        """增量列改写：旧版本 Parquet 的 static 列 + staging delta 新列 → 新版本目录

        与 PG 的 insert_select_from_base_delta 语义对齐（LEFT JOIN 保留全部对象行，
        无 delta 匹配的新列取 NULL）；removed 列不 SELECT 即消失。

        Args:
            dest_table: 新版本目录名（{wide_table}_{vh8}）
            base_table: 旧版本 Parquet 目录绝对路径
            delta_table: PG staging delta 表名（None 表示仅删除列变化，纯列裁剪）
            etl_date: 'YYYY-MM-DD'

        Returns:
            新版本行数（= 旧版本行数，对账保证）
        """
        etl = date.fromisoformat(etl_date)
        new_dir = self.date_dir(dest_table, etl)
        old_glob = (
            (Path(base_table) / f"etl_date={etl_date}" / PARQUET_FILE_PATTERN).as_posix()
        )
        if not Path(base_table).is_dir():
            raise RuntimeError(f"[duckdb] 增量基准目录不存在: {base_table}")

        old_relation = f"read_parquet('{old_glob}', hive_partitioning=false)"
        tmp_dir = new_dir.with_name(new_dir.name + ".tmp")
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
        tmp_dir.mkdir(parents=True)

        select_cols = (
            ["s.target_id"]
            + [f"s.{c}" for c in static_cols]
            + [f"d.{c}" for c in inc_cols]
            + ["s.etl_date"]
        )
        join_clause = (
            f"LEFT JOIN pg_src.public.{delta_table} d "
            f"ON s.target_id = d.target_id AND s.etl_date = d.etl_date"
            if delta_table else ""
        )
        copy_sql = (
            f"COPY (SELECT {', '.join(select_cols)} "
            f"FROM {old_relation} s {join_clause}) "
            f"TO '{(tmp_dir / 'part-00000.parquet').as_posix()}' "
            f"(FORMAT PARQUET, COMPRESSION {self._compression})"
        )

        conn = self._attach_pg()
        try:
            logger.debug(f"[duckdb] 增量COPY SQL: {copy_sql}")
            conn.execute(copy_sql)

            # 对账：行数守恒（LEFT JOIN 不丢行；重复target_id会被对账暴露）
            new_relation = self._parquet_relation(tmp_dir)
            old_rows = conn.execute(f"SELECT count(*) FROM {old_relation}").fetchone()[0]
            new_rows = conn.execute(f"SELECT count(*) FROM {new_relation}").fetchone()[0]
            if new_rows != old_rows:
                raise RuntimeError(
                    f"[duckdb] 增量对账失败: 新版本行数({new_rows}) != 旧版本行数({old_rows})"
                )
        finally:
            try:
                conn.execute("DETACH pg_src")
            except Exception:
                pass
            conn.close()

        self._atomic_landing(tmp_dir, new_dir)
        logger.info(
            f"[duckdb] 增量落盘完成: {new_dir}, {new_rows}行, "
            f"static={len(static_cols)}, inc={len(inc_cols)}"
        )
        return int(new_rows)

    def snapshot_ref(self, table_name: str, etl_date: date) -> str:
        """快照引用为版本 Parquet 目录绝对路径"""
        return str(self.version_dir(table_name).resolve())

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

    def _build_copy_sql(self, staging_table: str, tmp_dir: Path) -> str:
        """COPY staging → Parquet（排除 created_at 审计列）"""
        target = (tmp_dir / "part-00000.parquet").as_posix()
        return (
            f"COPY (SELECT * EXCLUDE (created_at) FROM pg_src.public.{staging_table}) "
            f"TO '{target}' (FORMAT PARQUET, COMPRESSION {self._compression})"
        )

    def _build_checksum_sql(self, relation: str, columns: List[str]) -> str:
        """构建行数 + 顺序无关内容校验和（sum(hash(行拼接))）"""
        joined = ", ".join(f"{col}::VARCHAR" for col in columns)
        return f"SELECT count(*), sum(hash(concat_ws('|', {joined}))) FROM {relation}"

    def _reconcile(self, conn, staging_table: str, tmp_dir: Path, spark_rows: int) -> None:
        """三方对账：不一致即抛异常（不落盘、不DROP staging）"""
        self._reconcile_relations(
            conn,
            staging_relation=f"pg_src.public.{staging_table}",
            parquet_relation=self._parquet_relation(tmp_dir),
            spark_rows=spark_rows,
        )

    def _reconcile_relations(self, conn, staging_relation: str, parquet_relation: str,
                             spark_rows: int | None) -> None:
        parquet_cols = [
            row[0] for row in conn.execute(
                f"DESCRIBE SELECT * FROM {parquet_relation}"
            ).fetchall()
        ]
        staging_cols = [
            row[0] for row in conn.execute(
                f"DESCRIBE SELECT * FROM {staging_relation}"
            ).fetchall()
        ]

        # 列集合一致（staging 允许多出 created_at 审计列）
        extra = [c for c in parquet_cols if c not in staging_cols]
        if extra:
            raise RuntimeError(f"[duckdb] 对账失败: parquet多出staging不存在的列: {extra}")

        parquet_n, parquet_hash = conn.execute(
            self._build_checksum_sql(parquet_relation, parquet_cols)
        ).fetchone()
        staging_n, staging_hash = conn.execute(
            self._build_checksum_sql(staging_relation, parquet_cols)
        ).fetchone()

        # spark_rows 仅同步链路有（互转场景为 None，跳过该侧核对）
        if spark_rows is not None and spark_rows != staging_n:
            raise RuntimeError(
                f"[duckdb] 对账失败: Spark行数({spark_rows}) != staging行数({staging_n})"
            )
        if staging_n != parquet_n:
            raise RuntimeError(
                f"[duckdb] 对账失败: staging行数({staging_n}) != parquet行数({parquet_n})"
            )
        if staging_hash != parquet_hash:
            raise RuntimeError(
                f"[duckdb] 对账失败: 内容校验和不一致 "
                f"(staging={staging_hash}, parquet={parquet_hash})"
            )
        logger.info(
            f"[duckdb] 三方对账通过: 行数={parquet_n}, checksum={parquet_hash}"
        )

    @staticmethod
    def _parquet_relation(tmp_dir: Path) -> str:
        glob = (tmp_dir / PARQUET_FILE_PATTERN).as_posix()
        return f"read_parquet('{glob}')"

    @staticmethod
    def _atomic_landing(tmp_dir: Path, final_dir: Path) -> None:
        """临时目录原子落盘：tmp → final（若 final 已存在先挪走再删）"""
        if not tmp_dir.exists():
            raise RuntimeError(f"[duckdb] 临时目录不存在，无法落盘: {tmp_dir}")

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

    # ------------------------------------------------------------------
    # 互转原语（阶段5：PG离线表 ↔ Parquet 按日期互转，与同步路径同源）
    # ------------------------------------------------------------------

    def pull_pg_partition_to_parquet(
        self,
        pg_table: str,
        etl_date: date,
        dest_dir: Path,
    ) -> Tuple[int, int, int]:
        """PG 正式宽表指定日期分区 → Parquet 目录（pg2duckdb 核心）

        与 staging 全量路径同源：COPY 列式直转 → 对账 → 原子落盘。

        Returns:
            (row_count, column_count, file_size_bytes)
        """
        tmp_dir = dest_dir.with_name(dest_dir.name + ".tmp")
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
        tmp_dir.mkdir(parents=True)

        conn = self._attach_pg()
        try:
            conn.execute(self._build_partition_copy_sql(pg_table, etl_date, tmp_dir))

            # 对账：PG分区行数+内容 vs parquet行数+内容（同一DuckDB会话内完成）
            date_str = etl_date.strftime('%Y-%m-%d')
            source_relation = (
                f"(SELECT * EXCLUDE (created_at) FROM pg_src.public.{pg_table} "
                f"WHERE etl_date = DATE '{date_str}')"
            )
            source_rows = conn.execute(
                f"SELECT count(*) FROM {source_relation}"
            ).fetchone()[0]
            self._reconcile_relations(
                conn, source_relation, self._parquet_relation(tmp_dir), source_rows
            )
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
        return (int(source_rows), len(parquet_cols), size_bytes)

    def push_parquet_to_pg(
        self,
        version_dir: Path,
        etl_date: date,
        pg_table: str,
        indicator_metadata: dict,
    ) -> int:
        """Parquet 指定日期目录 → PG 正式宽表分区（duckdb2pg 应急回退通道）

        先经 PgStore.ensure_table 建表+分区，再经 DuckDB 读写 ATTACH 流式写入，
        写后对账（行数+checksum）。created_at 审计列不搬运（PG 默认值生成）。

        Returns:
            写入行数
        """
        self._pg_writer.ensure_table(pg_table, indicator_metadata, etl_date)

        date_str = etl_date.strftime('%Y-%m-%d')
        parquet_relation = (
            f"read_parquet('{(version_dir / f'etl_date={date_str}' / PARQUET_FILE_PATTERN).as_posix()}', "
            f"hive_partitioning=false)"
        )

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
            conn.execute(f"ATTACH '{escaped}' AS pg_rw (TYPE POSTGRES);")
            conn.execute(
                f"INSERT INTO pg_rw.public.{pg_table} "
                f"SELECT * FROM {parquet_relation}"
            )

            # 对账：写入后 PG 分区 vs parquet
            pg_relation = (
                f"(SELECT * EXCLUDE (created_at) FROM pg_rw.public.{pg_table} "
                f"WHERE etl_date = DATE '{date_str}')"
            )
            self._reconcile_relations(conn, pg_relation, parquet_relation, None)
            row_count = conn.execute(f"SELECT count(*) FROM {pg_relation}").fetchone()[0]
        finally:
            try:
                conn.execute("DETACH pg_rw")
            except Exception:
                pass
            conn.close()

        return int(row_count)

    def _build_partition_copy_sql(self, pg_table: str, etl_date: date, tmp_dir: Path) -> str:
        """PG 正式表按日期过滤 COPY → Parquet（分区裁剪下推到PG）"""
        target = (tmp_dir / "part-00000.parquet").as_posix()
        return (
            f"COPY (SELECT * EXCLUDE (created_at) FROM pg_src.public.{pg_table} "
            f"WHERE etl_date = DATE '{etl_date.strftime('%Y-%m-%d')}') "
            f"TO '{target}' (FORMAT PARQUET, COMPRESSION {self._compression})"
        )
