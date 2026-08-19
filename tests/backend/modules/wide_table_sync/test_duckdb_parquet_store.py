"""
阶段3：DuckdbParquetStore —— staging 中转全量路径

对应 docs/fraudhunter_offline_dual_store_plan.md 阶段3：
- 目录/表名规范（§2.2/§2.3）：_staging_ 前缀 UNLOGGED、版本+日期双隔离目录；
- COPY SQL 生成：排除 created_at 审计列、带压缩配置；
- 三方对账：本地 DuckDB 用 read_parquet 双侧关系验证（行数/内容checksum/失败路径）；
- 原子落盘：tmp → final、final 已存在时替换、tmp 缺失时报错；
- 快照引用为 Parquet 目录绝对路径。

ATTACH 真实 PG 的部分属集成测试（docker PG），此处不覆盖。
"""

import importlib.util
import sys
import types
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_backend_root = Path(__file__).parents[4] / "backend"
sys.path.insert(0, str(_backend_root))

_store_pkg_root = _backend_root / "services" / "fraudhunter" / "wide_table_service" / "store"


def _load_duckdb_store(monkeypatch, storage_path="/tmp/test_wide_tables_parquet"):
    """加载 store 包（stub 掉 config/logger/analyze_db_utils）"""
    services_module = types.ModuleType("services")
    fraudhunter_module = types.ModuleType("services.fraudhunter")
    wide_table_service_module = types.ModuleType("services.fraudhunter.wide_table_service")

    config_module = types.ModuleType("utils.config")
    config_module.settings = types.SimpleNamespace(
        pyspark_enabled=False,
        fraudhunter_realtime_writer_batch_insert_size=500,
        fraudhunter_wide_table_offline_store="duckdb",
        fraudhunter_wide_table_duckdb_storage_path=storage_path,
        fraudhunter_wide_table_duckdb_compression="zstd",
        fraudhunter_analyze_db={"postgresql": {}},
    )

    logger_module = types.ModuleType("utils.logger")
    logger_module.logger = types.SimpleNamespace(
        debug=lambda *a, **k: None,
        info=lambda *a, **k: None,
        warning=lambda *a, **k: None,
        error=lambda *a, **k: None,
    )

    analyze_db_utils_module = types.ModuleType("utils.analyze_db_utils")
    analyze_db_utils_module.AnalyzeDBConnector = object
    manager = MagicMock()
    analyze_db_utils_module.AnalyzeDBPartitionManager = manager

    for name, module in {
        "services": services_module,
        "services.fraudhunter": fraudhunter_module,
        "services.fraudhunter.wide_table_service": wide_table_service_module,
        "utils.config": config_module,
        "utils.logger": logger_module,
        "utils.analyze_db_utils": analyze_db_utils_module,
    }.items():
        monkeypatch.setitem(sys.modules, name, module)

    def _exec(rel_path, mod_name):
        spec = importlib.util.spec_from_file_location(mod_name, _store_pkg_root / rel_path)
        module = importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules, mod_name, module)
        spec.loader.exec_module(module)
        return module

    _exec("base.py", "services.fraudhunter.wide_table_service.store.base")
    _exec("pg_store.py", "services.fraudhunter.wide_table_service.store.pg_store")
    duckdb_module = _exec(
        "duckdb_parquet_store.py",
        "services.fraudhunter.wide_table_service.store.duckdb_parquet_store",
    )
    _exec("__init__.py", "services.fraudhunter.wide_table_service.store")

    return duckdb_module, manager


ETL = date(2026, 8, 19)


class TestNamingAndPaths:
    def test_staging_table_name(self, monkeypatch):
        module, _ = _load_duckdb_store(monkeypatch)
        assert module.DuckdbParquetStore.staging_table_name("cust_wide_table_abcd1234", ETL) \
            == "_staging_cust_wide_table_abcd1234_20260819"

    def test_directory_convention(self, monkeypatch, tmp_path):
        module, _ = _load_duckdb_store(monkeypatch, storage_path=str(tmp_path))
        store = module.DuckdbParquetStore()

        date_dir = store.date_dir("cust_wide_table_abcd1234", ETL)
        assert date_dir == tmp_path / "cust_wide_table_abcd1234" / "etl_date=2026-08-19"

    def test_snapshot_ref_is_absolute_version_dir(self, monkeypatch, tmp_path):
        module, _ = _load_duckdb_store(monkeypatch, storage_path=str(tmp_path / "nested"))
        store = module.DuckdbParquetStore()

        ref = store.snapshot_ref("cust_wide_table_abcd1234", ETL)
        assert ref.startswith("/")
        assert "nested/cust_wide_table_abcd1234" in ref
        assert "etl_date=" not in ref  # 快照引用到版本目录，查询时按日期拼 glob


class TestEnsureTable:
    def test_ensure_table_recreates_unlogged_staging(self, monkeypatch, tmp_path):
        module, manager = _load_duckdb_store(monkeypatch, storage_path=str(tmp_path))
        store = module.DuckdbParquetStore()
        metadata = {"1": {"indicator_code": "i1"}}

        store.ensure_table("cust_wide_table_abcd1234", metadata, ETL)

        staging = "_staging_cust_wide_table_abcd1234_20260819"
        manager.drop_table.assert_called_once_with(staging)
        manager.create_heap_table.assert_called_once_with(staging, metadata, unlogged=True)

    def test_storage_root_created(self, monkeypatch, tmp_path):
        module, _ = _load_duckdb_store(monkeypatch, storage_path=str(tmp_path / "root"))
        store = module.DuckdbParquetStore()

        store.ensure_table("t", {}, ETL)

        assert (tmp_path / "root").is_dir()

    def test_delta_merge_requires_existing_base_dir(self, monkeypatch, tmp_path):
        """增量合并的基准目录必须存在（阶段6增量路径前置校验）"""
        module, _ = _load_duckdb_store(monkeypatch, storage_path=str(tmp_path))
        store = module.DuckdbParquetStore()
        with pytest.raises(RuntimeError, match="基准目录不存在"):
            store.merge_delta_insert_select(
                "t_new", str(tmp_path / "missing_base"), None, {}, [], [], "2026-08-19"
            )


class TestCopySql:
    def test_copy_excludes_created_at_and_sets_compression(self, monkeypatch, tmp_path):
        module, _ = _load_duckdb_store(monkeypatch, storage_path=str(tmp_path))
        store = module.DuckdbParquetStore()

        sql = store._build_copy_sql("_staging_t_20260819", tmp_path / "etl_date=2026-08-19.tmp")

        assert "SELECT * EXCLUDE (created_at) FROM pg_src.public._staging_t_20260819" in sql
        assert "FORMAT PARQUET" in sql
        assert "COMPRESSION zstd" in sql
        assert "etl_date=2026-08-19.tmp/part-00000.parquet" in sql


class TestReconciliation:
    """本地 DuckDB 验证对账逻辑（双侧均用 read_parquet 关系）"""

    def _make_store_and_conn(self, monkeypatch, tmp_path):
        module, _ = _load_duckdb_store(monkeypatch, storage_path=str(tmp_path))
        store = module.DuckdbParquetStore()
        import duckdb
        return store, duckdb.connect()

    @staticmethod
    def _write_parquet(conn, path: Path, rows: str):
        path.parent.mkdir(parents=True, exist_ok=True)
        conn.execute(
            f"COPY (SELECT * FROM ({rows})) TO '{path.as_posix()}' (FORMAT PARQUET)"
        )

    def test_reconcile_passes_on_identical_data(self, monkeypatch, tmp_path):
        store, conn = self._make_store_and_conn(monkeypatch, tmp_path)
        staging_file = tmp_path / "staging" / "part-00000.parquet"
        parquet_file = tmp_path / "target" / "part-00000.parquet"
        rows = "SELECT 'A001' AS target_id, DATE '2026-08-19' AS etl_date, 100 AS i_amt"
        self._write_parquet(conn, staging_file, rows)
        self._write_parquet(conn, parquet_file, rows)

        store._reconcile_relations(
            conn,
            staging_relation=f"read_parquet('{staging_file.as_posix()}')",
            parquet_relation=f"read_parquet('{parquet_file.as_posix()}')",
            spark_rows=1,
        )

    def test_reconcile_detects_row_count_mismatch(self, monkeypatch, tmp_path):
        store, conn = self._make_store_and_conn(monkeypatch, tmp_path)
        staging_file = tmp_path / "staging" / "part-00000.parquet"
        parquet_file = tmp_path / "target" / "part-00000.parquet"
        one = "SELECT 'A001' AS target_id, DATE '2026-08-19' AS etl_date, 100 AS i_amt"
        two = one + " UNION ALL SELECT 'A002' AS target_id, DATE '2026-08-19' AS etl_date, 200 AS i_amt"
        self._write_parquet(conn, staging_file, two)
        self._write_parquet(conn, parquet_file, one)

        with pytest.raises(RuntimeError, match="staging行数.*!= parquet行数"):
            store._reconcile_relations(
                conn,
                staging_relation=f"read_parquet('{staging_file.as_posix()}')",
                parquet_relation=f"read_parquet('{parquet_file.as_posix()}')",
                spark_rows=2,
            )

    def test_reconcile_detects_spark_vs_staging_mismatch(self, monkeypatch, tmp_path):
        store, conn = self._make_store_and_conn(monkeypatch, tmp_path)
        staging_file = tmp_path / "staging" / "part-00000.parquet"
        parquet_file = tmp_path / "target" / "part-00000.parquet"
        rows = "SELECT 'A001' AS target_id, DATE '2026-08-19' AS etl_date, 100 AS i_amt"
        self._write_parquet(conn, staging_file, rows)
        self._write_parquet(conn, parquet_file, rows)

        with pytest.raises(RuntimeError, match="Spark行数"):
            store._reconcile_relations(
                conn,
                staging_relation=f"read_parquet('{staging_file.as_posix()}')",
                parquet_relation=f"read_parquet('{parquet_file.as_posix()}')",
                spark_rows=99,
            )

    def test_reconcile_detects_content_mismatch(self, monkeypatch, tmp_path):
        store, conn = self._make_store_and_conn(monkeypatch, tmp_path)
        staging_file = tmp_path / "staging" / "part-00000.parquet"
        parquet_file = tmp_path / "target" / "part-00000.parquet"
        self._write_parquet(
            conn, staging_file,
            "SELECT 'A001' AS target_id, DATE '2026-08-19' AS etl_date, 100 AS i_amt",
        )
        self._write_parquet(
            conn, parquet_file,
            "SELECT 'A001' AS target_id, DATE '2026-08-19' AS etl_date, 999 AS i_amt",
        )

        with pytest.raises(RuntimeError, match="内容校验和不一致"):
            store._reconcile_relations(
                conn,
                staging_relation=f"read_parquet('{staging_file.as_posix()}')",
                parquet_relation=f"read_parquet('{parquet_file.as_posix()}')",
                spark_rows=1,
            )

    def test_reconcile_ignores_staging_extra_audit_column(self, monkeypatch, tmp_path):
        """staging 多出 created_at 审计列不影响对账（COPY时已排除）"""
        store, conn = self._make_store_and_conn(monkeypatch, tmp_path)
        staging_file = tmp_path / "staging" / "part-00000.parquet"
        parquet_file = tmp_path / "target" / "part-00000.parquet"
        self._write_parquet(
            conn, staging_file,
            "SELECT 'A001' AS target_id, DATE '2026-08-19' AS etl_date, 100 AS i_amt, "
            "now() AS created_at",
        )
        self._write_parquet(
            conn, parquet_file,
            "SELECT 'A001' AS target_id, DATE '2026-08-19' AS etl_date, 100 AS i_amt",
        )

        store._reconcile_relations(
            conn,
            staging_relation=f"read_parquet('{staging_file.as_posix()}')",
            parquet_relation=f"read_parquet('{parquet_file.as_posix()}')",
            spark_rows=1,
        )


class TestAtomicLanding:
    def test_prepare_tmp_dir_creates_nested_parents(self, monkeypatch, tmp_path):
        """DuckDB COPY 不自动建父目录——_prepare_tmp_dir 统一自动创建多层目录"""
        module, _ = _load_duckdb_store(monkeypatch, storage_path=str(tmp_path))
        final_dir = tmp_path / "cust_wide_table_abcd1234" / "etl_date=2026-08-19"

        tmp_dir = module.DuckdbParquetStore._prepare_tmp_dir(final_dir)

        assert tmp_dir == final_dir.with_name("etl_date=2026-08-19.tmp")
        assert tmp_dir.is_dir()

    def test_prepare_tmp_dir_clears_stale_content(self, monkeypatch, tmp_path):
        """幂等：上次失败残留的 tmp 目录被清空重建，旧 part 文件不混入"""
        module, _ = _load_duckdb_store(monkeypatch, storage_path=str(tmp_path))
        final_dir = tmp_path / "etl_date=2026-08-19"
        stale = final_dir.with_name("etl_date=2026-08-19.tmp")
        stale.mkdir()
        (stale / "part-stale.parquet").write_bytes(b"stale")

        tmp_dir = module.DuckdbParquetStore._prepare_tmp_dir(final_dir)

        assert tmp_dir.is_dir()
        assert list(tmp_dir.iterdir()) == []

    def test_lands_tmp_to_final(self, monkeypatch, tmp_path):
        module, _ = _load_duckdb_store(monkeypatch, storage_path=str(tmp_path))
        tmp_dir = tmp_path / "etl_date=2026-08-19.tmp"
        final_dir = tmp_path / "etl_date=2026-08-19"
        tmp_dir.mkdir()
        (tmp_dir / "part-00000.parquet").write_bytes(b"parquet")

        module.DuckdbParquetStore._atomic_landing(tmp_dir, final_dir)

        assert (final_dir / "part-00000.parquet").exists()
        assert not tmp_dir.exists()

    def test_replaces_existing_final(self, monkeypatch, tmp_path):
        module, _ = _load_duckdb_store(monkeypatch, storage_path=str(tmp_path))
        tmp_dir = tmp_path / "etl_date=2026-08-19.tmp"
        final_dir = tmp_path / "etl_date=2026-08-19"
        final_dir.mkdir()
        (final_dir / "old.parquet").write_bytes(b"old")
        tmp_dir.mkdir()
        (tmp_dir / "part-00000.parquet").write_bytes(b"new")

        module.DuckdbParquetStore._atomic_landing(tmp_dir, final_dir)

        assert list(final_dir.iterdir()) == [final_dir / "part-00000.parquet"]
        assert (final_dir / "part-00000.parquet").read_bytes() == b"new"

    def test_raises_when_tmp_missing(self, monkeypatch, tmp_path):
        module, _ = _load_duckdb_store(monkeypatch, storage_path=str(tmp_path))
        with pytest.raises(RuntimeError, match="临时目录不存在"):
            module.DuckdbParquetStore._atomic_landing(
                tmp_path / "missing.tmp", tmp_path / "etl_date=2026-08-19"
            )
