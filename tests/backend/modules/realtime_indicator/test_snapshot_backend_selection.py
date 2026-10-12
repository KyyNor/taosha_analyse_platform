"""
Issue #9 + 二期阶段 9：快照选择尊重读后端配置（统一策略防调用点漂移）

覆盖 query_router 的公共选择函数（realtime_indicator_job._get_latest_offline_snapshot
与 ModelExecutor._get_latest_version_snapshot 均委托至此）：
- 读后端 = read_backend 显式配置；未配置时 offline_store=duckdb 读 duckdb，其余读 postgresql
  （both 未配置读后端 = 影子写，线上仍读 PG）
- 读后端无快照时回退最新一条并告警
- validate_store_config 读写/计算模式组合校验
以及生产调用点确实接入了公共函数（源码级防漂移）。
"""

import importlib.util
import sys
import types
from datetime import date, datetime
from pathlib import Path

import pytest

_backend_root = Path(__file__).parents[4] / "backend"
sys.path.insert(0, str(_backend_root))

ETL = date(2026, 9, 10)


def _fake_settings(offline_store, read_backend=None):
    return types.SimpleNamespace(
        fraudhunter_wide_table_offline_store=offline_store,
        fraudhunter_wide_table_read_backend=read_backend,
    )


def _load_query_router(monkeypatch, offline_store, read_backend=None):
    for name in ('services', 'services.fraudhunter',
                 'services.fraudhunter.wide_table_service',
                 'services.fraudhunter.wide_table_service.store'):
        monkeypatch.setitem(sys.modules, name, sys.modules.get(name) or types.ModuleType(name))
    config_module = types.ModuleType('utils.config')
    config_module.settings = _fake_settings(offline_store, read_backend)
    monkeypatch.setitem(sys.modules, 'utils.config', config_module)
    logger_module = types.ModuleType('utils.logger')
    logger_module.logger = types.SimpleNamespace(
        debug=lambda *a, **k: None, info=lambda *a, **k: None,
        warning=lambda *a, **k: None, error=lambda *a, **k: None,
    )
    monkeypatch.setitem(sys.modules, 'utils.logger', logger_module)

    spec = importlib.util.spec_from_file_location(
        'services.fraudhunter.wide_table_service.store.query_router',
        _backend_root / 'services' / 'fraudhunter' / 'wide_table_service' / 'store' / 'query_router.py',
    )
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(
        sys.modules, 'services.fraudhunter.wide_table_service.store.query_router', module)
    spec.loader.exec_module(module)
    return module


def _snap(backend, generation_time, etl_date=ETL):
    return types.SimpleNamespace(
        wide_table_name='cust_wide_table',
        version_hash='hash_abcd1234' * 4,
        etl_date=etl_date,
        generation_time=generation_time,
        storage_backend=backend,
        parquet_file_path=(
            '/data/wt/cust_wide_table_hash_abcd' if backend == 'duckdb'
            else 'cust_wide_table_hash_abcd1234_hash_abcd1234_20260910'
        ),
    )


def _dual_snapshots():
    """同日期双后端快照：DuckDB 生成更晚（both 双写下典型时序）"""
    return [
        _snap('duckdb', datetime(2026, 9, 10, 6, 30, 0)),
        _snap('postgresql', datetime(2026, 9, 10, 6, 0, 0)),
    ]


class TestPreferredBackend:
    def test_postgresql_mode_prefers_pg(self, monkeypatch):
        qr = _load_query_router(monkeypatch, 'postgresql')
        assert qr.preferred_snapshot_backend() == 'postgresql'
        assert qr.offline_store_uses_duckdb() is False

    def test_duckdb_mode_prefers_duckdb(self, monkeypatch):
        qr = _load_query_router(monkeypatch, 'duckdb')
        assert qr.preferred_snapshot_backend() == 'duckdb'
        assert qr.offline_store_uses_duckdb() is True

    def test_both_mode_without_read_backend_prefers_pg(self, monkeypatch):
        """both 未配置读后端 = 影子写：线上仍读 PG，DuckDB 维护任务按写配置启用"""
        qr = _load_query_router(monkeypatch, 'both')
        assert qr.preferred_snapshot_backend() == 'postgresql'
        assert qr.offline_store_uses_duckdb() is True

    def test_write_read_matrix(self, monkeypatch):
        expected = {
            ('postgresql', None): 'postgresql',
            ('postgresql', 'postgresql'): 'postgresql',
            ('both', None): 'postgresql',
            ('both', 'postgresql'): 'postgresql',
            ('both', 'duckdb'): 'duckdb',
            ('duckdb', None): 'duckdb',
            ('duckdb', 'duckdb'): 'duckdb',
            ('duckdb', 'postgresql'): 'postgresql',
        }
        for (write, read), want in expected.items():
            qr = _load_query_router(monkeypatch, write, read)
            assert qr.preferred_snapshot_backend() == want, (write, read)

    def test_read_backend_case_insensitive(self, monkeypatch):
        qr = _load_query_router(monkeypatch, 'both', ' DuckDB ')
        assert qr.preferred_snapshot_backend() == 'duckdb'


class TestSelectSnapshot:
    def test_postgresql_mode_picks_pg_even_if_duckdb_newer(self, monkeypatch):
        """切回 postgresql 后实时任务不再选中生成更晚的 DuckDB 快照"""
        qr = _load_query_router(monkeypatch, 'postgresql')
        picked = qr.select_snapshot_by_preferred_backend(_dual_snapshots())
        assert qr.snapshot_backend(picked) == 'postgresql'

    def test_duckdb_mode_picks_duckdb(self, monkeypatch):
        qr = _load_query_router(monkeypatch, 'duckdb')
        picked = qr.select_snapshot_by_preferred_backend(_dual_snapshots())
        assert qr.snapshot_backend(picked) == 'duckdb'

    def test_both_mode_default_picks_pg(self, monkeypatch):
        """both 影子写：即使 DuckDB 快照更新，线上仍选 PG 快照"""
        qr = _load_query_router(monkeypatch, 'both')
        picked = qr.select_snapshot_by_preferred_backend(_dual_snapshots())
        assert qr.snapshot_backend(picked) == 'postgresql'

    def test_both_mode_read_duckdb_picks_duckdb(self, monkeypatch):
        qr = _load_query_router(monkeypatch, 'both', 'duckdb')
        picked = qr.select_snapshot_by_preferred_backend(_dual_snapshots())
        assert qr.snapshot_backend(picked) == 'duckdb'

    def test_fallback_to_latest_when_preferred_missing(self, monkeypatch):
        """偏好后端完全没有快照时回退最新一条（告警），避免直接不可用"""
        qr = _load_query_router(monkeypatch, 'postgresql')
        picked = qr.select_snapshot_by_preferred_backend([
            _snap('duckdb', datetime(2026, 9, 10, 7, 0, 0)),
            _snap('duckdb', datetime(2026, 9, 10, 6, 0, 0)),
        ])
        assert qr.snapshot_backend(picked) == 'duckdb'

    def test_empty_and_none_inputs(self, monkeypatch):
        qr = _load_query_router(monkeypatch, 'postgresql')
        assert qr.select_snapshot_by_preferred_backend([]) is None
        assert qr.select_snapshot_by_preferred_backend([None]) is None

    def test_legacy_snapshot_without_backend_field_treated_as_pg(self, monkeypatch):
        """未迁移存量行（无 storage_backend 列值）兜底按 postgresql 处理"""
        qr = _load_query_router(monkeypatch, 'postgresql')
        legacy = types.SimpleNamespace(
            generation_time=datetime(2026, 9, 10, 8, 0, 0))
        picked = qr.select_snapshot_by_preferred_backend([legacy])
        assert picked is legacy  # 兜底 postgresql = 偏好命中


class TestValidateStoreConfig:
    def _qr(self, monkeypatch):
        return _load_query_router(monkeypatch, 'postgresql')

    def test_valid_combinations_no_warning(self, monkeypatch):
        qr = self._qr(monkeypatch)
        for write, read in (('postgresql', None), ('both', None), ('both', 'duckdb'),
                            ('duckdb', None), ('duckdb', 'duckdb')):
            assert qr.validate_store_config(write, read, 'local') == [], (write, read)
            assert qr.validate_store_config(write, read, 'remote') == [], (write, read)

    def test_write_pg_read_duckdb_rejected(self, monkeypatch):
        qr = self._qr(monkeypatch)
        with pytest.raises(ValueError, match='read_backend'):
            qr.validate_store_config('postgresql', 'duckdb')

    def test_write_duckdb_read_pg_warns(self, monkeypatch):
        qr = self._qr(monkeypatch)
        warnings = qr.validate_store_config('duckdb', 'postgresql')
        assert len(warnings) == 1 and '停止更新' in warnings[0]

    def test_invalid_values_rejected(self, monkeypatch):
        qr = self._qr(monkeypatch)
        with pytest.raises(ValueError, match='offline_store'):
            qr.validate_store_config('mysql', None)
        with pytest.raises(ValueError, match='read_backend'):
            qr.validate_store_config('both', 'both')
        with pytest.raises(ValueError, match='duck_compute.mode'):
            qr.validate_store_config('both', None, 'cloud')

    def test_delegate_only_for_ds(self, monkeypatch):
        qr = self._qr(monkeypatch)
        with pytest.raises(ValueError, match='delegate'):
            qr.validate_store_config('both', None, 'delegate', role='backend')
        assert qr.validate_store_config('both', None, 'delegate', role='ds') == []


class TestProdCallSitesWired:
    """生产调用点接入公共选择函数（源码级防漂移，镜像 test_duckdb_mode_sql 策略）"""

    def test_realtime_job_delegates_to_shared_selector(self):
        source = (
            _backend_root / "services" / "scheduler" / "jobs" / "realtime_indicator_job.py"
        ).read_text(encoding="utf-8")
        assert "select_snapshot_by_preferred_backend" in source
        # 不得再按裸时间序 first() 取快照（Issue #9 修复点）
        assert "desc(FraudHunterWideTableSnapshot.generation_time)\n    ).first()" not in source

    def test_model_executor_delegates_to_shared_selector(self):
        source = (
            _backend_root / "services" / "fraudhunter" / "model_service" / "model_executor.py"
        ).read_text(encoding="utf-8")
        assert "select_snapshot_by_preferred_backend" in source
