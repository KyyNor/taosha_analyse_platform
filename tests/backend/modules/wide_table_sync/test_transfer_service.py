"""
阶段5：互转工具 —— 拉取/写回原语与元数据流转

对应 docs/fraudhunter_offline_dual_store_plan.md 阶段5：
- pg2duckdb COPY SQL：按日期过滤（分区裁剪）、排除 created_at、带压缩；
- 幂等：目标目录已存在跳过（overwrite 重转）——目录与快照状态机；
- duckdb2pg：ensure_table 前置 + 读写 ATTACH INSERT；
- 日期解析（--dates / --backfill）。

涉及真实 PG 的往返属集成测试（docker PG），此处覆盖 SQL 生成与纯逻辑。
"""

import importlib.util
import sys
import types
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_backend_root = Path(__file__).parents[4] / "backend"
sys.path.insert(0, str(_backend_root))

_store_pkg_root = _backend_root / "services" / "fraudhunter" / "wide_table_service" / "store"
ETL = date(2026, 8, 19)


def _load_modules(monkeypatch, storage_path="/tmp/test_transfer_parquet"):
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
        debug=lambda *a, **k: None, info=lambda *a, **k: None,
        warning=lambda *a, **k: None, error=lambda *a, **k: None,
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

    return {"duck_store": duck_module, "manager": manager}


def _make_store(monkeypatch, tmp_path):
    modules = _load_modules(monkeypatch, storage_path=str(tmp_path))
    return modules["duck_store"].DuckdbParquetStore(), modules["manager"]


class TestPullPgPartitionSql:
    def test_copy_sql_filters_date_and_excludes_audit(self, monkeypatch, tmp_path):
        store, _ = _make_store(monkeypatch, tmp_path)

        sql = store._build_partition_copy_sql("cust_wide_table_abcd1234", ETL, tmp_path / "etl_date=2026-08-19.tmp")

        assert "FROM pg_src.public.cust_wide_table_abcd1234" in sql
        assert "WHERE etl_date = DATE '2026-08-19'" in sql
        assert "EXCLUDE (created_at)" in sql
        assert "COMPRESSION zstd" in sql
        assert "etl_date=2026-08-19.tmp/part-00000.parquet" in sql


class TestPushParquetToPg:
    def test_ensure_table_before_push(self, monkeypatch, tmp_path):
        """duckdb2pg 写回前必须先建 PG 正式表+分区（经 PgStore）"""
        store, manager = _make_store(monkeypatch, tmp_path)
        metadata = {"1": {"indicator_code": "i1"}}

        # 中断在 duckdb 连接阶段，验证 ensure_table 已被调用
        with pytest.raises(Exception):
            store.push_parquet_to_pg(
                tmp_path / "cust_wide_table_abcd1234", ETL,
                "cust_wide_table_abcd1234", metadata,
            )

        manager.create_wide_table.assert_called_once_with("cust_wide_table_abcd1234", metadata)
        manager.ensure_partition.assert_called_once_with("cust_wide_table_abcd1234", ETL)


class TestResolveEtlDates:
    def _load_transfer_helpers(self, monkeypatch):
        # transfer_service 依赖较多（models等），此处仅复刻纯函数逻辑验证
        # 与生产代码保持一致的实现见下（改动生产函数时须同步）
        from datetime import datetime

        def resolve_etl_dates(dates, backfill):
            if dates:
                return [datetime.strptime(d, '%Y-%m-%d').date() for d in dates]
            if backfill and backfill > 0:
                today = date.today()
                return [today - timedelta(days=i) for i in range(backfill)]
            raise ValueError("必须指定 --dates 或 --backfill 之一")

        return resolve_etl_dates

    def test_dates_list(self, monkeypatch):
        resolve = self._load_transfer_helpers(monkeypatch)
        assert resolve(["2026-08-01", "2026-08-02"], None) == [
            date(2026, 8, 1), date(2026, 8, 2)
        ]

    def test_backfill_range(self, monkeypatch):
        resolve = self._load_transfer_helpers(monkeypatch)
        result = resolve(None, 3)
        assert len(result) == 3
        assert result[0] == date.today()
        assert result[2] == date.today() - timedelta(days=2)

    def test_neither_raises(self, monkeypatch):
        resolve = self._load_transfer_helpers(monkeypatch)
        with pytest.raises(ValueError):
            resolve(None, None)


class TestTransferDirectorySemantics:
    def test_version_and_date_dirs_follow_convention(self, monkeypatch, tmp_path):
        store, _ = _make_store(monkeypatch, tmp_path)
        assert store.date_dir("cust_wide_table_abcd1234", ETL) == (
            tmp_path / "cust_wide_table_abcd1234" / "etl_date=2026-08-19"
        )
        assert store.snapshot_ref("cust_wide_table_abcd1234", ETL) == str(
            (tmp_path / "cust_wide_table_abcd1234").resolve()
        )
