"""
tests/backend/modules/pg_partition_export/test_pg_partition_export.py
======================================================================
单元测试：PG 表分区导出 Parquet CLI（自双存储方案阶段5移植的单一能力）

背景说明（代码调研摘要）：
    被测模块： backend/scripts/pg_partition_export.py
        - PgPartitionExporter.export_partition  核心导出流程
        - _build_partition_copy_sql             COPY SQL（分区裁剪/审计列排除/压缩）
        - _build_checksum_sql                   对账校验和 SQL
        - _prepare_tmp_dir / _atomic_landing    临时目录与原子落盘
        - resolve_etl_dates                     CLI 日期参数解析

测试策略：
    ✅ SQL 构建器 / 目录操作 / 日期解析 → 纯逻辑，无 IO
    ✅ export_partition 主流程 → Mock DuckDB 连接（不需要 duckdb 包与真实 PG）
    ⚠️ 真实 PG ↔ DuckDB 互转 → 属集成测试，本文件不覆盖
"""

import atexit
import sys
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_backend_root = Path(__file__).parents[4] / "backend"
sys.path.insert(0, str(_backend_root))

# utils.config 模块底部有全局单例，import 时要求 backend/config/config.yaml 存在（已gitignore）。
# 本地缺失时临时创建，测试结束恢复（与 wide_table_sync 测试同款兜底）。
_default_config_yaml = _backend_root / "config" / "config.yaml"
_created_default_config = False
if not _default_config_yaml.exists():
    _default_config_yaml.write_text("app:\n  name: taosha-test\n", encoding="utf-8")
    _created_default_config = True


def _cleanup_default_config():
    if _created_default_config:
        try:
            _default_config_yaml.unlink()
        except OSError:
            pass


atexit.register(_cleanup_default_config)

from scripts.pg_partition_export import (  # noqa: E402
    PgPartitionExporter,
    resolve_etl_dates,
    build_dest_dir,
)


# =============================================================================
# PART A — COPY / 对账 SQL 构建
# =============================================================================

class TestBuildPartitionCopySql:

    def test_copy_sql_filters_by_date_and_excludes_audit_column(self, tmp_path):
        """COPY SQL 必须按日期分区裁剪，并排除 created_at 审计列。"""
        sql = PgPartitionExporter._build_partition_copy_sql(
            PgPartitionExporter(), "cust_wide_table_a1b2c3d4",
            date(2026, 8, 1), tmp_path,
        )
        assert "FROM pg_src.public.cust_wide_table_a1b2c3d4" in sql
        assert "WHERE etl_date = DATE '2026-08-01'" in sql
        assert "EXCLUDE (created_at)" in sql
        assert "FORMAT PARQUET" in sql

    def test_copy_sql_targets_part_file_in_tmp_dir(self, tmp_path):
        """COPY 目标必须是 tmp 目录下的 part-00000.parquet（原子落盘前提）。"""
        sql = PgPartitionExporter._build_partition_copy_sql(
            PgPartitionExporter(), "t1", date(2026, 8, 1), tmp_path,
        )
        assert f"TO '{(tmp_path / 'part-00000.parquet').as_posix()}'" in sql

    def test_copy_sql_uses_configured_compression(self, tmp_path):
        exporter = PgPartitionExporter(compression="snappy")
        sql = exporter._build_partition_copy_sql("t1", date(2026, 8, 1), tmp_path)
        assert "COMPRESSION snappy" in sql


class TestBuildChecksumSql:

    def test_checksum_counts_and_hashes_all_columns_as_varchar(self):
        sql = PgPartitionExporter._build_checksum_sql("rel", ["a", "b"])
        assert sql == (
            "SELECT count(*), sum(hash(concat_ws('|', a::VARCHAR, b::VARCHAR))) FROM rel"
        )


# =============================================================================
# PART B — 临时目录与原子落盘
# =============================================================================

class TestTmpDirAndAtomicLanding:

    def test_prepare_tmp_dir_creates_and_cleans_stale_residue(self, tmp_path):
        final_dir = tmp_path / "etl_date=2026-08-01"
        stale = final_dir.with_name(final_dir.name + ".tmp")
        stale.mkdir(parents=True)
        (stale / "part-old.parquet").write_bytes(b"stale")

        tmp_dir = PgPartitionExporter._prepare_tmp_dir(final_dir)

        assert tmp_dir.is_dir()
        assert not (tmp_dir / "part-old.parquet").exists(), "上次残留不能混入本次对账"

    def test_atomic_landing_replaces_existing_final_dir(self, tmp_path):
        final_dir = tmp_path / "etl_date=2026-08-01"
        final_dir.mkdir()
        (final_dir / "part-old.parquet").write_bytes(b"old")
        tmp_dir = final_dir.with_name(final_dir.name + ".tmp")
        tmp_dir.mkdir()
        (tmp_dir / "part-new.parquet").write_bytes(b"new")

        PgPartitionExporter._atomic_landing(tmp_dir, final_dir)

        assert (final_dir / "part-new.parquet").read_bytes() == b"new"
        assert not (final_dir / "part-old.parquet").exists()
        assert not tmp_dir.exists()
        assert not final_dir.with_name(final_dir.name + ".trash").exists()

    def test_atomic_landing_without_tmp_raises(self, tmp_path):
        final_dir = tmp_path / "etl_date=2026-08-01"
        with pytest.raises(RuntimeError, match="临时目录不存在"):
            PgPartitionExporter._atomic_landing(tmp_path / "nope", final_dir)


# =============================================================================
# PART C — CLI 日期解析与目录布局
# =============================================================================

class TestResolveEtlDates:

    def test_explicit_dates(self):
        assert resolve_etl_dates(["2026-08-01", "2026-08-02"], None) == [
            date(2026, 8, 1), date(2026, 8, 2),
        ]

    def test_backfill_includes_today(self):
        today = date.today()
        assert resolve_etl_dates(None, 3) == [today, today - timedelta(days=1), today - timedelta(days=2)]

    def test_neither_raises(self):
        with pytest.raises(ValueError, match="--dates 或 --backfill"):
            resolve_etl_dates(None, None)


class TestDestDirLayout:

    def test_hive_style_layout(self, tmp_path):
        dest = build_dest_dir(tmp_path, "cust_wide_table_a1b2c3d4", date(2026, 8, 1))
        assert dest == tmp_path / "cust_wide_table_a1b2c3d4" / "etl_date=2026-08-01"


# =============================================================================
# PART D — export_partition 主流程（Mock DuckDB 连接）
# =============================================================================

def _make_conn(rows=5, cols=("target_id", "i_a", "i_b"), checksum=999):
    """构造脚本化 Mock 连接：DESCRIBE→列名，其余 fetchone→(rows, checksum)"""
    conn = MagicMock()
    result = MagicMock()
    result.fetchall.return_value = [(c,) for c in cols]
    result.fetchone.return_value = (rows, checksum)
    conn.execute.return_value = result
    return conn


class TestExportPartitionFlow:

    def test_happy_path_lands_parquet_dir(self, tmp_path, monkeypatch):
        """对账通过后 tmp 原子落盘为最终目录，返回 (行数, 列数, 字节数)。"""
        conn = _make_conn(rows=5, checksum=111)
        exporter = PgPartitionExporter()
        monkeypatch.setattr(exporter, "_attach_pg", lambda: conn)

        dest_dir = tmp_path / "t1" / "etl_date=2026-08-01"
        rows, cols, size = exporter.export_partition("t1", date(2026, 8, 1), dest_dir)

        assert (rows, cols) == (5, 3)
        assert dest_dir.is_dir()
        # Mock 连接不落真实 part 文件，size 字节数此时为 0（真机导出有值）
        # DETACH 必须被调用（READ_ONLY 会话也显式释放）
        executed = [call.args[0] for call in conn.execute.call_args_list]
        assert any(sql.startswith("COPY (SELECT * EXCLUDE (created_at)") for sql in executed)
        assert any(sql == "DETACH pg_src" for sql in executed)

    def test_checksum_mismatch_blocks_landing(self, tmp_path, monkeypatch):
        """源表与 parquet 内容校验和不一致时抛异常，且不落盘。"""
        conn = MagicMock()
        conn.execute.return_value.fetchone.side_effect = [
            (5,),      # SELECT count(*) 分区行数
            (5, 111),  # parquet checksum
            (5, 222),  # 源表 checksum → 不一致
        ]
        conn.execute.return_value.fetchall.return_value = [("target_id",), ("i_a",)]
        exporter = PgPartitionExporter()
        monkeypatch.setattr(exporter, "_attach_pg", lambda: conn)

        dest_dir = tmp_path / "t1" / "etl_date=2026-08-01"
        with pytest.raises(RuntimeError, match="内容校验和不一致"):
            exporter.export_partition("t1", date(2026, 8, 1), dest_dir)

        assert not dest_dir.exists(), "对账失败不得落盘"

    def test_row_count_mismatch_blocks_landing(self, tmp_path, monkeypatch):
        """parquet 行数与源表分区行数不一致时抛异常，且不落盘。"""
        conn = MagicMock()
        conn.execute.return_value.fetchone.side_effect = [
            (5,),      # SELECT count(*) 分区行数
            (4, 111),  # parquet: 4 行 → 与分区 5 行不一致
            (5, 111),  # 源表侧 checksum（行数与分区一致，暴露 parquet 缺行）
        ]
        conn.execute.return_value.fetchall.return_value = [("target_id",)]
        exporter = PgPartitionExporter()
        monkeypatch.setattr(exporter, "_attach_pg", lambda: conn)

        dest_dir = tmp_path / "t1" / "etl_date=2026-08-01"
        with pytest.raises(RuntimeError, match="parquet行数"):
            exporter.export_partition("t1", date(2026, 8, 1), dest_dir)

        assert not dest_dir.exists()
