"""
阶段7：双写对账 —— 配对逻辑测试

对应 docs/fraudhunter_offline_dual_store_plan.md 阶段7：
both 灰度期间，同一 (宽表, 版本, 日期) 双后端均有 ready 快照才构成对账组；
单后端/非ready/超回溯窗口的不参与。
"""

import asyncio
import importlib.util
import sys
import types
from datetime import date, datetime, timedelta
from pathlib import Path

_backend_root = Path(__file__).parents[4] / "backend"
sys.path.insert(0, str(_backend_root))


def _load_reconcile_job(monkeypatch):
    config_module = types.ModuleType("utils.config")
    config_module.settings = types.SimpleNamespace()
    logger_module = types.ModuleType("utils.logger")
    logger_module.logger = types.SimpleNamespace(
        debug=lambda *a, **k: None, info=lambda *a, **k: None,
        warning=lambda *a, **k: None, error=lambda *a, **k: None,
    )
    db_base_module = types.ModuleType("models.db_base")

    class _FakeCtx:
        def __enter__(self):
            return types.SimpleNamespace(query=lambda *a, **k: _FakeQuery())

        def __exit__(self, *args):
            return False

    db_base_module.get_db_session = _FakeCtx
    model_module = types.ModuleType("models.fraudhunter.wide_table")

    from sqlalchemy import column

    class _SnapshotStub:
        # 可比较的列对象（filter表达式在stub查询下不会真正求值）
        etl_date = column("etl_date")
        status = column("status")
        version_hash = column("version_hash")

    model_module.FraudHunterWideTableSnapshot = _SnapshotStub

    for name, module in {
        "utils.config": config_module,
        "utils.logger": logger_module,
        "models": types.ModuleType("models"),
        "models.fraudhunter": types.ModuleType("models.fraudhunter"),
        "models.db_base": db_base_module,
        "models.fraudhunter.wide_table": model_module,
    }.items():
        monkeypatch.setitem(sys.modules, name, module)

    spec = importlib.util.spec_from_file_location(
        "dual_store_reconcile_job_for_test",
        _backend_root / "services" / "scheduler" / "jobs" / "dual_store_reconcile_job.py",
    )
    job = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(job)
    return job


class _FakeQuery:
    """模拟 _find_dual_pairs 的服务端过滤语义（ready + 近7天 + 版本非空）"""
    snapshots = []

    def filter(self, *args, **kwargs):
        return self

    def all(self):
        since = date.today() - timedelta(days=7)
        return [
            s for s in _FakeQuery.snapshots
            if s.status == 'ready'
            and s.version_hash is not None
            and s.etl_date >= since
        ]


def _snap(wide_table, version_hash, etl_date, backend, status='ready'):
    return types.SimpleNamespace(
        wide_table_name=wide_table,
        version_hash=version_hash,
        etl_date=etl_date,
        storage_backend=backend,
        status=status,
        parquet_file_path=(
            f"{wide_table}_{version_hash[:8]}" if version_hash else ""
        ) if backend == 'postgresql'
        else f"/data/wide_tables/{wide_table}_{version_hash[:8] if version_hash else 'na'}",
    )


def _fake_db():
    return types.SimpleNamespace(query=lambda *a, **k: _FakeQuery())


class TestFindDualPairs:
    def test_paired_when_both_backends_ready(self, monkeypatch):
        job = _load_reconcile_job(monkeypatch)
        today = date.today()
        _FakeQuery.snapshots = [
            _snap("cust_wide_table", "hash_abcd1234" * 4, today, 'postgresql'),
            _snap("cust_wide_table", "hash_abcd1234" * 4, today, 'duckdb'),
        ]

        with_pairs = job._find_dual_pairs(_fake_db())
        assert len(with_pairs) == 1
        (wt, vh, d), pg, duck = with_pairs[0]
        assert wt == "cust_wide_table"
        assert pg.storage_backend == 'postgresql'
        assert duck.storage_backend == 'duckdb'

    def test_single_backend_not_paired(self, monkeypatch):
        job = _load_reconcile_job(monkeypatch)
        _FakeQuery.snapshots = [
            _snap("cust_wide_table", "hash_abcd1234" * 4, date.today(), 'postgresql'),
        ]
        assert job._find_dual_pairs(_fake_db()) == []

    def test_failed_snapshot_excluded(self, monkeypatch):
        job = _load_reconcile_job(monkeypatch)
        _FakeQuery.snapshots = [
            _snap("cust_wide_table", "hash_abcd1234" * 4, date.today(), 'postgresql'),
            _snap("cust_wide_table", "hash_abcd1234" * 4, date.today(), 'duckdb', status='failed'),
        ]
        assert job._find_dual_pairs(_fake_db()) == []

    def test_realtime_null_version_excluded(self, monkeypatch):
        job = _load_reconcile_job(monkeypatch)
        _FakeQuery.snapshots = [
            _snap("dep_acct_wide_table_realtime", None, date.today(), 'postgresql'),
            _snap("dep_acct_wide_table_realtime", None, date.today(), 'duckdb'),
        ]
        assert job._find_dual_pairs(_fake_db()) == []

    def test_out_of_lookback_excluded(self, monkeypatch):
        job = _load_reconcile_job(monkeypatch)
        old_date = date.today() - timedelta(days=job.RECONCILE_LOOKBACK_DAYS + 1)
        _FakeQuery.snapshots = [
            _snap("cust_wide_table", "hash_abcd1234" * 4, old_date, 'postgresql'),
            _snap("cust_wide_table", "hash_abcd1234" * 4, old_date, 'duckdb'),
        ]
        assert job._find_dual_pairs(_fake_db()) == []

    def test_job_noop_without_pairs(self, monkeypatch):
        """无双后端快照对时任务安全空跑"""
        job = _load_reconcile_job(monkeypatch)
        _FakeQuery.snapshots = []
        asyncio.run(job.dual_store_reconcile_job())  # 不抛异常即通过
