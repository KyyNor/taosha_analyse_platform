"""
阶段2：存储抽象层 —— 工厂路由与 PG 实现委托测试

对应 docs/fraudhunter_offline_dual_store_plan.md 阶段2（纯重构，行为不变）：
- get_store 按配置返回正确实现（postgresql 现状路径）；
- PgWideTableStore 到 AnalyzeDBPartitionManager 的调用参数透传；
- write_pivot 按 pyspark_enabled 分发 PySpark/JDBC 两条写入路径（原逻辑迁入）；
- 验收断言：sync_service.py 不再直接调用存储写路径。
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


def _load_store_modules(monkeypatch, offline_store="postgresql", pyspark_enabled=False,
                        storage_path="/tmp/test_wide_tables_parquet"):
    """加载 store 包（stub 掉 config/logger/analyze_db_utils）"""
    services_module = types.ModuleType("services")
    fraudhunter_module = types.ModuleType("services.fraudhunter")
    wide_table_service_module = types.ModuleType("services.fraudhunter.wide_table_service")

    config_module = types.ModuleType("utils.config")
    config_module.settings = types.SimpleNamespace(
        pyspark_enabled=pyspark_enabled,
        fraudhunter_realtime_writer_batch_insert_size=500,
        fraudhunter_wide_table_offline_store=offline_store,
        fraudhunter_wide_table_duckdb_storage_path=storage_path,
        fraudhunter_wide_table_duckdb_compression="zstd",
        fraudhunter_analyze_db={"postgresql": {
            "host": "127.0.0.1", "port": 5432, "database": "taosha_fraudhunter",
            "user": "taosha", "password": "secret'",
        }},
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
    analyze_db_utils_module.AnalyzeDBPartitionManager = MagicMock()

    store_pkg_module = types.ModuleType("services.fraudhunter.wide_table_service.store")

    for name, module in {
        "services": services_module,
        "services.fraudhunter": fraudhunter_module,
        "services.fraudhunter.wide_table_service": wide_table_service_module,
        "utils.config": config_module,
        "utils.logger": logger_module,
        "utils.analyze_db_utils": analyze_db_utils_module,
        "services.fraudhunter.wide_table_service.store": store_pkg_module,
    }.items():
        monkeypatch.setitem(sys.modules, name, module)

    def _exec(rel_path, mod_name):
        spec = importlib.util.spec_from_file_location(mod_name, _store_pkg_root / rel_path)
        module = importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules, mod_name, module)
        spec.loader.exec_module(module)
        return module

    base_module = _exec("base.py", "services.fraudhunter.wide_table_service.store.base")
    pg_module = _exec("pg_store.py", "services.fraudhunter.wide_table_service.store.pg_store")
    duckdb_module = _exec(
        "duckdb_parquet_store.py",
        "services.fraudhunter.wide_table_service.store.duckdb_parquet_store",
    )
    init_module = _exec("__init__.py", "services.fraudhunter.wide_table_service.store")

    return {
        "base": base_module,
        "pg_store": pg_module,
        "duckdb_store": duckdb_module,
        "factory": init_module,
        "analyze_db_utils": analyze_db_utils_module,
        "config": config_module,
    }


class TestGetStoreFactory:
    def test_returns_pg_store_for_postgresql(self, monkeypatch):
        modules = _load_store_modules(monkeypatch, offline_store="postgresql")
        store = modules["factory"].get_store()
        assert isinstance(store, modules["pg_store"].PgWideTableStore)
        assert store.name == "postgresql"

    def test_explicit_backend_overrides_config(self, monkeypatch):
        modules = _load_store_modules(monkeypatch, offline_store="duckdb")
        store = modules["factory"].get_store("postgresql")
        assert isinstance(store, modules["pg_store"].PgWideTableStore)

    def test_duckdb_backend_returns_duckdb_store(self, monkeypatch):
        """阶段3起 duckdb 后端可用（staging 中转全量路径）"""
        modules = _load_store_modules(monkeypatch, offline_store="duckdb")
        store = modules["factory"].get_store()
        assert isinstance(store, modules["duckdb_store"].DuckdbParquetStore)
        assert store.name == "duckdb"
        assert store.supports_delta_insert_select is False

    def test_resolve_stores_both_returns_pg_first(self, monkeypatch):
        """both 模式：PG先、Parquet后（串行双写顺序）"""
        modules = _load_store_modules(monkeypatch, offline_store="both")
        stores = modules["factory"].resolve_stores()
        assert [s.name for s in stores] == ["postgresql", "duckdb"]

    def test_resolve_stores_single_backend(self, monkeypatch):
        modules = _load_store_modules(monkeypatch, offline_store="duckdb")
        stores = modules["factory"].resolve_stores()
        assert [s.name for s in stores] == ["duckdb"]

    def test_get_store_rejects_both(self, monkeypatch):
        """both 不作为单store返回（由 resolve_stores 拆分）"""
        modules = _load_store_modules(monkeypatch, offline_store="both")
        with pytest.raises(ValueError):
            modules["factory"].get_store()

    def test_unknown_backend_raises(self, monkeypatch):
        modules = _load_store_modules(monkeypatch, offline_store="mysql")
        with pytest.raises(ValueError, match="不支持的离线宽表存储后端"):
            modules["factory"].get_store()

    def test_config_default_is_postgresql(self, monkeypatch):
        """settings 缺失该属性时兜底 postgresql（阶段1默认值语义）"""
        modules = _load_store_modules(monkeypatch, offline_store="postgresql")
        del modules["config"].settings.fraudhunter_wide_table_offline_store
        store = modules["factory"].get_store()
        assert isinstance(store, modules["pg_store"].PgWideTableStore)


class TestPgStoreDelegation:
    """PgStore 到 AnalyzeDBPartitionManager 的调用映射（参数透传）"""

    def _store_and_manager(self, monkeypatch, pyspark_enabled=False):
        modules = _load_store_modules(monkeypatch, pyspark_enabled=pyspark_enabled)
        store = modules["pg_store"].PgWideTableStore()
        return store, modules["analyze_db_utils"].AnalyzeDBPartitionManager

    def test_ensure_table_creates_wide_table_and_partition(self, monkeypatch):
        store, manager = self._store_and_manager(monkeypatch)
        metadata = {"1": {"indicator_code": "i1"}}
        etl = date(2026, 8, 19)

        store.ensure_table("cust_wide_table_abcd1234", metadata, etl)

        manager.create_wide_table.assert_called_once_with("cust_wide_table_abcd1234", metadata)
        manager.ensure_partition.assert_called_once_with("cust_wide_table_abcd1234", etl)

    def test_create_heap_table_and_drop_table_passthrough(self, monkeypatch):
        store, manager = self._store_and_manager(monkeypatch)
        metadata = {"1": {"indicator_code": "i1"}}

        store.create_heap_table("_delta_t_20260819", metadata)
        store.drop_table("_delta_t_20260819")

        manager.create_heap_table.assert_called_once_with("_delta_t_20260819", metadata)
        manager.drop_table.assert_called_once_with("_delta_t_20260819")

    def test_merge_delta_insert_select_passthrough(self, monkeypatch):
        store, manager = self._store_and_manager(monkeypatch)
        manager.insert_select_from_base_delta.return_value = 12345

        row_count = store.merge_delta_insert_select(
            dest_table="t_new",
            base_table="t_old_20260819",
            delta_table="_delta_t_new_20260819",
            target_metadata={"1": {"indicator_code": "i1"}},
            static_cols=["i_static"],
            inc_cols=["i_changed"],
            etl_date="2026-08-19",
        )

        assert row_count == 12345
        _, kwargs = manager.insert_select_from_base_delta.call_args
        assert kwargs == {
            "dest_table": "t_new",
            "base_table": "t_old_20260819",
            "delta_table": "_delta_t_new_20260819",
            "target_metadata": {"1": {"indicator_code": "i1"}},
            "static_cols": ["i_static"],
            "inc_cols": ["i_changed"],
            "etl_date": "2026-08-19",
        }

    def test_snapshot_ref_returns_table_name(self, monkeypatch):
        store, _ = self._store_and_manager(monkeypatch)
        assert store.snapshot_ref("dep_acct_wide_table_abcd1234", date(2026, 8, 19)) \
            == "dep_acct_wide_table_abcd1234"

    def test_write_pivot_dispatches_pyspark(self, monkeypatch):
        store, _ = self._store_and_manager(monkeypatch, pyspark_enabled=True)
        monkeypatch.setattr(
            store, "_execute_with_pyspark_to_pg",
            lambda sql, table, refresh: (11, 4), raising=True
        )

        result = store.write_pivot("SELECT 1", "t", date(2026, 8, 19), refresh_sql="refresh table s")

        assert result == (11, 4)

    def test_write_pivot_dispatches_jdbc(self, monkeypatch):
        store, _ = self._store_and_manager(monkeypatch, pyspark_enabled=False)
        monkeypatch.setattr(
            store, "_execute_with_jdbc_to_pg",
            lambda sql, table, etl_date, refresh: (22, 5), raising=True
        )

        result = store.write_pivot("SELECT 1", "t", date(2026, 8, 19), refresh_sql="refresh table s")

        assert result == (22, 5)

    def test_is_wide_table_store_subclass(self, monkeypatch):
        modules = _load_store_modules(monkeypatch)
        store = modules["pg_store"].PgWideTableStore()
        assert isinstance(store, modules["base"].WideTableStore)


class TestSyncServiceWritePathAcceptance:
    """阶段2验收标准：sync_service.py 不再直接调用存储写路径"""

    _WRITE_PATH_CALLS = (
        "create_wide_table",
        "ensure_partition",
        "create_heap_table",
        "insert_select_from_base_delta",
        "copy_static_columns",
        "merge_aux_into_main",
        "drop_table",
    )

    _READ_PATH_CALLS = {"table_exists", "count_partition_rows"}

    def _sync_service_source(self):
        return (
            _backend_root / "services" / "fraudhunter" / "wide_table_service" / "sync_service.py"
        ).read_text(encoding="utf-8")

    def test_sync_service_has_no_direct_write_path_calls(self):
        import re

        source = self._sync_service_source()
        # 每个写路径调用点的前缀必须是 store. / self._store.（经存储抽象层路由）
        allowed_prefixes = ("store.", "self._store.")
        for call in self._WRITE_PATH_CALLS:
            for match in re.finditer(re.escape(call) + r"\s*\(", source):
                matched = any(
                    source[max(0, match.start() - len(p)):match.start()] == p
                    for p in allowed_prefixes
                )
                assert matched, (
                    f"sync_service.py 仍直接调用存储写路径: {call}（应经 WideTableStore）"
                )

    def test_analyze_db_usage_is_read_path_only(self):
        """sync_service 中残留的 AnalyzeDBPartitionManager 调用仅限只读探测"""
        import re

        source = self._sync_service_source()
        called_attrs = set(re.findall(r"AnalyzeDBPartitionManager\.(\w+)", source))

        assert called_attrs <= self._READ_PATH_CALLS, (
            f"出现写路径调用: {called_attrs - self._READ_PATH_CALLS}"
        )

    def test_moved_methods_no_longer_in_sync_service(self):
        source = self._sync_service_source()

        for method in (
            "_execute_with_pyspark_to_pg",
            "_execute_with_jdbc_to_pg",
            "_execute_spark_query_and_write_pg",
            "_copy_static_and_merge_incr",
        ):
            assert method not in source, f"方法 {method} 应已迁入 store 或删除"

    def test_dead_pyspark_parquet_method_removed(self):
        source = (_backend_root / "utils" / "spark_utils.py").read_text(encoding="utf-8")
        assert "execute_sql_to_parquet" not in source, "死方法 execute_sql_to_parquet 应删除"
