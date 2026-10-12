"""
阶段6：DuckDB 增量路径 —— 本地列改写与引用计数清理

对应 docs/fraudhunter_offline_dual_store_plan.md 阶段6：
- merge_delta_insert_select 生成的增量 COPY SQL：LEFT JOIN 语义（对齐PG insert-select）、
  static 列取旧 Parquet、inc 列取 delta、removed 列消失；
- 本地 DuckDB 端到端：构造旧版本 Parquet + delta 关系，验证合并、行数守恒对账；
- 引用计数清理：被快照引用的目录不删、无引用且过宽限期的目录删除、tmp/trash 残留清理。
"""

import asyncio
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
ETL = date(2026, 8, 19)


def _load_store_module(monkeypatch, storage_path):
    services_module = types.ModuleType("services")
    fraudhunter_module = types.ModuleType("services.fraudhunter")
    wide_table_service_module = types.ModuleType("services.fraudhunter.wide_table_service")

    config_module = types.ModuleType("utils.config")
    config_module.settings = types.SimpleNamespace(
        pyspark_enabled=False,
        fraudhunter_realtime_writer_batch_insert_size=500,
        fraudhunter_wide_table_offline_store="duckdb",
        fraudhunter_wide_table_duckdb_storage_path=str(storage_path),
        fraudhunter_wide_table_duckdb_compression="zstd",
        fraudhunter_analyze_db={"postgresql": {}},
    )
    logger_module = types.ModuleType("utils.logger")
    logger_module.logger = types.SimpleNamespace(
        debug=lambda *a, **k: None, info=lambda *a, **k: None,
        warning=lambda *a, **k: None, error=lambda *a, **k: None,
    )
    analyze_db_utils_module = types.ModuleType("utils.analyze_db_utils")
    analyze_db_utils_module.AnalyzeDBConnector = object
    analyze_db_utils_module.AnalyzeDBPartitionManager = MagicMock()

    for name, module in {
        "services": services_module,
        "services.fraudhunter": fraudhunter_module,
        "services.fraudhunter.wide_table_service": wide_table_service_module,
        "utils.config": config_module,
        "utils.logger": logger_module,
        "utils.analyze_db_utils": analyze_db_utils_module,
    }.items():
        monkeypatch.setitem(sys.modules, name, module)

    def _exec(rel, mod_name):
        spec = importlib.util.spec_from_file_location(mod_name, _store_pkg_root / rel)
        module = importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules, mod_name, module)
        spec.loader.exec_module(module)
        return module

    _exec("base.py", "services.fraudhunter.wide_table_service.store.base")
    _exec("pg_store.py", "services.fraudhunter.wide_table_service.store.pg_store")
    duck_module = _exec(
        "duckdb_parquet_store.py",
        "services.fraudhunter.wide_table_service.store.duckdb_parquet_store",
    )
    _exec("__init__.py", "services.fraudhunter.wide_table_service.store")
    return duck_module


class TestDeltaMergeSqlShape:
    """增量 COPY SQL 生成（字符串级验证，不依赖PG）"""

    def test_supports_delta_flag(self, monkeypatch, tmp_path):
        module = _load_store_module(monkeypatch, tmp_path)
        assert module.DuckdbParquetStore.supports_delta_insert_select is True

    def test_removed_only_change_has_no_join(self, monkeypatch, tmp_path):
        """仅删除列（inc_cols为空）→ 纯列裁剪，无JOIN无staging"""
        module = _load_store_module(monkeypatch, tmp_path)
        store = module.DuckdbParquetStore()

        base_dir = tmp_path / "cust_wide_table_old1234"
        (base_dir / "etl_date=2026-08-19").mkdir(parents=True)

        captured = {}

        class _FakeConn:
            def execute(self, sql):
                captured.setdefault('sqls', []).append(sql)
                if sql.startswith("COPY"):
                    return self
                class _R:
                    def fetchone(self):
                        return (2,)
                return _R()

            def close(self):
                pass

        monkeypatch.setattr(store, "_attach_pg", lambda: _FakeConn())
        rows = store.merge_delta_insert_select(
            dest_table="cust_wide_table_new1234",
            base_table=str(base_dir),
            delta_table=None,
            target_metadata={},
            static_cols=["i_static"],
            inc_cols=[],
            etl_date="2026-08-19",
        )
        assert rows == 2
        copy_sql = next(s for s in captured['sqls'] if s.startswith("COPY"))
        assert "s.target_id, s.i_static, s.etl_date" in copy_sql
        assert "JOIN" not in copy_sql

    def test_base_dir_missing_raises(self, monkeypatch, tmp_path):
        module = _load_store_module(monkeypatch, tmp_path)
        store = module.DuckdbParquetStore()
        with pytest.raises(RuntimeError, match="基准目录不存在"):
            store.merge_delta_insert_select(
                dest_table="t_new", base_table=str(tmp_path / "missing"),
                delta_table="_d", target_metadata={},
                static_cols=[], inc_cols=["i_x"], etl_date="2026-08-19",
            )

class TestDeltaMergeLocalEndToEnd:
    """本地 DuckDB 验证增量合并语义（双侧 read_parquet 关系模拟）"""

    def _prepare_parquet(self, tmp_path):
        import duckdb

        old_dir = tmp_path / "cust_wide_table_old1234" / "etl_date=2026-08-19"
        old_dir.mkdir(parents=True)
        conn = duckdb.connect()
        conn.execute(f"""
            COPY (
                SELECT * FROM (
                    VALUES
                    ('A001', DATE '2026-08-19', 100, 'oldx'),
                    ('A002', DATE '2026-08-19', 200, 'oldy'),
                    ('A003', DATE '2026-08-19', 300, 'oldz')
                ) AS t(target_id, etl_date, i_static, i_changed)
            ) TO '{(old_dir / 'part-00000.parquet').as_posix()}' (FORMAT PARQUET)
        """)
        conn.close()
        return old_dir

    def test_left_join_semantics_preserve_all_rows(self, monkeypatch, tmp_path):
        """LEFT JOIN：delta 缺失的对象行保留，新列取 NULL（对齐PG语义）"""
        module = _load_store_module(monkeypatch, tmp_path)
        store = module.DuckdbParquetStore()
        old_dir = self._prepare_parquet(tmp_path)

        # delta 仅含 A001/A002（A003 无新值）
        import duckdb

        conn = duckdb.connect()
        delta_rows = "(SELECT * FROM (VALUES ('A001', DATE '2026-08-19', 'newx'), ('A002', DATE '2026-08-19', 'newy')) AS d(target_id, etl_date, i_changed))"

        # 用本地关系替换 ATTACH：monkeypatch _attach_pg 返回带视图的连接
        class _PgAttachConn:
            def __init__(self, real):
                self._real = real

            def execute(self, sql):
                # 将 pg_src.public._delta_ 替换为本地VALUES关系
                return self._real.execute(
                    sql.replace("pg_src.public._delta_t", delta_rows)
                )

            def close(self):
                self._real.close()

        real_conn = duckdb.connect()
        fake = _PgAttachConn(real_conn)
        monkeypatch.setattr(store, "_attach_pg", lambda: fake)

        new_dir = tmp_path / "cust_wide_table_new1234" / "etl_date=2026-08-19"
        rows = store.merge_delta_insert_select(
            dest_table="cust_wide_table_new1234",
            base_table=str(tmp_path / "cust_wide_table_old1234"),
            delta_table="_delta_t",
            target_metadata={},
            static_cols=["i_static"],
            inc_cols=["i_changed"],
            etl_date="2026-08-19",
        )

        assert rows == 3  # 行数守恒：A003 保留
        assert new_dir.is_dir()
        verify_conn = duckdb.connect()
        result = verify_conn.execute(f"""
            SELECT target_id, i_static, i_changed FROM read_parquet(
                '{(new_dir / 'part-00000.parquet').as_posix()}', hive_partitioning=false)
            ORDER BY target_id
        """).fetchall()
        assert result == [
            ("A001", 100, "newx"),
            ("A002", 200, "newy"),
            ("A003", 300, None),  # LEFT JOIN 语义
        ]


    def test_new_target_id_in_delta_aborts_merge(self, monkeypatch, tmp_path):
        """Issue #7：delta 出现旧版本不存在的 target_id → 显式中止，不静默丢行"""
        module = _load_store_module(monkeypatch, tmp_path)
        store = module.DuckdbParquetStore()
        old_dir = self._prepare_parquet(tmp_path)

        import duckdb

        # delta 含 A004（旧 Parquet 只有 A001~A003）
        delta_rows = ("(SELECT * FROM (VALUES "
                      "('A001', DATE '2026-08-19', 'newx'), "
                      "('A004', DATE '2026-08-19', 'newq')) AS d(target_id, etl_date, i_changed))")

        class _PgAttachConn:
            def __init__(self, real):
                self._real = real

            def execute(self, sql):
                return self._real.execute(
                    sql.replace("pg_src.public._delta_t", delta_rows)
                )

            def close(self):
                self._real.close()

        fake = _PgAttachConn(duckdb.connect())
        monkeypatch.setattr(store, "_attach_pg", lambda: fake)

        with pytest.raises(module.TargetUniverseChangedError, match="target_id"):
            store.merge_delta_insert_select(
                dest_table="cust_wide_table_new1234",
                base_table=str(tmp_path / "cust_wide_table_old1234"),
                delta_table="_delta_t",
                target_metadata={},
                static_cols=["i_static"],
                inc_cols=["i_changed"],
                etl_date="2026-08-19",
            )
        # 中止后不产生新版本目录（tmp 已在断言前保留供排障）
        new_dir = tmp_path / "cust_wide_table_new1234" / "etl_date=2026-08-19"
        assert not new_dir.exists()

    def test_unchanged_universe_passes_check(self, monkeypatch, tmp_path):
        """delta 全部命中旧 target_id → 校验通过，正常合并"""
        module = _load_store_module(monkeypatch, tmp_path)
        store = module.DuckdbParquetStore()
        self._prepare_parquet(tmp_path)

        import duckdb

        delta_rows = ("(SELECT * FROM (VALUES "
                      "('A001', DATE '2026-08-19', 'newx')) AS d(target_id, etl_date, i_changed))")

        class _PgAttachConn:
            def __init__(self, real):
                self._real = real

            def execute(self, sql):
                return self._real.execute(
                    sql.replace("pg_src.public._delta_t", delta_rows)
                )

            def close(self):
                self._real.close()

        fake = _PgAttachConn(duckdb.connect())
        monkeypatch.setattr(store, "_attach_pg", lambda: fake)

        rows = store.merge_delta_insert_select(
            dest_table="cust_wide_table_ok1234",
            base_table=str(tmp_path / "cust_wide_table_old1234"),
            delta_table="_delta_t",
            target_metadata={},
            static_cols=["i_static"],
            inc_cols=["i_changed"],
            etl_date="2026-08-19",
        )
        assert rows == 3  # 旧版本 3 行守恒


class TestParquetCleanupJob:
    """引用计数清理逻辑（替换引用集合查询，验证目录处置）"""

    def _load_job(self, monkeypatch, storage_path, referenced):
        spec = importlib.util.spec_from_file_location(
            "parquet_cleanup_job_for_test",
            _backend_root / "services" / "scheduler" / "jobs" / "parquet_cleanup_job.py",
        )
        job = importlib.util.module_from_spec(spec)

        config_module = types.ModuleType("utils.config")
        config_module.settings = types.SimpleNamespace(
            fraudhunter_wide_table_duckdb_storage_path=str(storage_path),
            fraudhunter_wide_table_duckdb_parquet_cleanup_grace_hours=0,
            # 清理逻辑本体仅在 offline_store 含 duckdb 时执行（Issue #10 no-op 守卫）
            fraudhunter_wide_table_offline_store='duckdb',
        )
        logger_module = types.ModuleType("utils.logger")
        logger_module.logger = types.SimpleNamespace(
            debug=lambda *a, **k: None, info=lambda *a, **k: None,
            warning=lambda *a, **k: None, error=lambda *a, **k: None,
        )
        db_base_module = types.ModuleType("models.db_base")
        db_base_module.get_db_session = None  # 不应被触达（引用集合被替换）

        wide_table_model_module = types.ModuleType("models.fraudhunter.wide_table")
        wide_table_model_module.FraudHunterWideTableSnapshot = object

        monkeypatch.setitem(sys.modules, "utils.config", config_module)
        monkeypatch.setitem(sys.modules, "utils.logger", logger_module)
        monkeypatch.setitem(sys.modules, "models", types.ModuleType("models"))
        monkeypatch.setitem(sys.modules, "models.fraudhunter", types.ModuleType("models.fraudhunter"))
        monkeypatch.setitem(sys.modules, "models.db_base", db_base_module)
        monkeypatch.setitem(sys.modules, "models.fraudhunter.wide_table", wide_table_model_module)
        spec.loader.exec_module(job)

        resolved = {Path(p).resolve().as_posix() for p in referenced}
        job._referenced_parquet_dirs = lambda: resolved
        return job

    def test_referenced_dir_kept_unreferenced_deleted(self, monkeypatch, tmp_path):
        """被引用目录保留；无引用目录删除"""
        keep_dir = tmp_path / "cust_wide_table_keep1234"
        drop_dir = tmp_path / "cust_wide_table_drop1234"
        for d in (keep_dir, drop_dir):
            d.mkdir()
            (d / "etl_date=2026-08-19").mkdir()
            (d / "etl_date=2026-08-19" / "part-00000.parquet").write_bytes(b"x")

        job = self._load_job(monkeypatch, tmp_path, referenced=[str(keep_dir)])
        asyncio.run(job.parquet_cleanup_job())

        assert keep_dir.exists()
        assert not drop_dir.exists()

    def test_stale_tmp_dir_cleaned(self, monkeypatch, tmp_path):
        tmp_dir = tmp_path / "etl_date=2026-08-19.tmp"
        tmp_dir.mkdir()
        (tmp_dir / "part-00000.parquet").write_bytes(b"x")

        job = self._load_job(monkeypatch, tmp_path, referenced=[])
        asyncio.run(job.parquet_cleanup_job())

        assert not tmp_dir.exists()

    def test_noop_when_offline_store_is_postgresql(self, monkeypatch, tmp_path):
        """Issue #10：纯 PG 模式 no-op——即使目录存在（历史残留/手工文件）也不清理"""
        stale_dir = tmp_path / "cust_wide_table_old1234"
        stale_dir.mkdir()
        (stale_dir / "etl_date=2026-08-19").mkdir()
        (stale_dir / "etl_date=2026-08-19" / "part-00000.parquet").write_bytes(b"x")

        job = self._load_job(monkeypatch, tmp_path, referenced=[])
        # job 模块持有的是 stub settings（_load_job 注入 sys.modules['utils.config']）
        stub_settings = sys.modules['utils.config'].settings
        stub_settings.fraudhunter_wide_table_offline_store = 'postgresql'
        try:
            asyncio.run(job.parquet_cleanup_job())
        finally:
            stub_settings.fraudhunter_wide_table_offline_store = 'duckdb'

        assert stale_dir.exists()  # 纯 PG 模式不执行目录清理
