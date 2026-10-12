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


def _load_reconcile_job(monkeypatch, offline_store='both'):
    config_module = types.ModuleType("utils.config")
    config_module.settings = types.SimpleNamespace(
        fraudhunter_wide_table_offline_store=offline_store,
    )
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

    # query_router stub: 提供 get_query_session 工厂（Issue #2 后对账经此执行）
    qr_module = types.ModuleType(
        "services.fraudhunter.wide_table_service.store.query_router")
    qr_module.get_query_session = lambda attach_pg=True: _FakeDuckSession()

    for name, module in {
        "utils.config": config_module,
        "utils.logger": logger_module,
        "models": types.ModuleType("models"),
        "models.fraudhunter": types.ModuleType("models.fraudhunter"),
        "models.db_base": db_base_module,
        "models.fraudhunter.wide_table": model_module,
        "services": types.ModuleType("services"),
        "services.fraudhunter": types.ModuleType("services.fraudhunter"),
        "services.fraudhunter.wide_table_service": types.ModuleType(
            "services.fraudhunter.wide_table_service"),
        "services.fraudhunter.wide_table_service.store": types.ModuleType(
            "services.fraudhunter.wide_table_service.store"),
        "services.fraudhunter.wide_table_service.store.query_router": qr_module,
    }.items():
        monkeypatch.setitem(sys.modules, name, module)

    spec = importlib.util.spec_from_file_location(
        "dual_store_reconcile_job_for_test",
        _backend_root / "services" / "scheduler" / "jobs" / "dual_store_reconcile_job.py",
    )
    job = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(job)
    return job, qr_module


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
        job, _ = _load_reconcile_job(monkeypatch)
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
        job, _ = _load_reconcile_job(monkeypatch)
        _FakeQuery.snapshots = [
            _snap("cust_wide_table", "hash_abcd1234" * 4, date.today(), 'postgresql'),
        ]
        assert job._find_dual_pairs(_fake_db()) == []

    def test_failed_snapshot_excluded(self, monkeypatch):
        job, _ = _load_reconcile_job(monkeypatch)
        _FakeQuery.snapshots = [
            _snap("cust_wide_table", "hash_abcd1234" * 4, date.today(), 'postgresql'),
            _snap("cust_wide_table", "hash_abcd1234" * 4, date.today(), 'duckdb', status='failed'),
        ]
        assert job._find_dual_pairs(_fake_db()) == []

    def test_realtime_null_version_excluded(self, monkeypatch):
        job, _ = _load_reconcile_job(monkeypatch)
        _FakeQuery.snapshots = [
            _snap("dep_acct_wide_table_realtime", None, date.today(), 'postgresql'),
            _snap("dep_acct_wide_table_realtime", None, date.today(), 'duckdb'),
        ]
        assert job._find_dual_pairs(_fake_db()) == []

    def test_out_of_lookback_excluded(self, monkeypatch):
        job, _ = _load_reconcile_job(monkeypatch)
        old_date = date.today() - timedelta(days=job.RECONCILE_LOOKBACK_DAYS + 1)
        _FakeQuery.snapshots = [
            _snap("cust_wide_table", "hash_abcd1234" * 4, old_date, 'postgresql'),
            _snap("cust_wide_table", "hash_abcd1234" * 4, old_date, 'duckdb'),
        ]
        assert job._find_dual_pairs(_fake_db()) == []

    def test_job_noop_without_pairs(self, monkeypatch):
        """无双后端快照对时任务安全空跑"""
        job, _ = _load_reconcile_job(monkeypatch)
        _FakeQuery.snapshots = []
        asyncio.run(job.dual_store_reconcile_job())  # 不抛异常即通过

    def test_job_noop_when_not_both_mode(self, monkeypatch):
        """Issue #10：offline_store 非 both（含默认 postgresql）时任务 no-op，
        即使存在双后端快照也不执行对账（get_query_session 不被触达）"""
        for store in ('postgresql', 'duckdb'):
            job, qr = _load_reconcile_job(monkeypatch, offline_store=store)
            _FakeQuery.snapshots = [
                _snap("cust_wide_table", "hash_abcd1234" * 4, date.today(), 'postgresql'),
                _snap("cust_wide_table", "hash_abcd1234" * 4, date.today(), 'duckdb'),
            ]
            touched = []
            qr.get_query_session = lambda attach_pg=True: touched.append(1)
            asyncio.run(job.dual_store_reconcile_job())
            assert not touched, f"offline_store={store} 时不应执行对账查询"


class _FakeDuckSession:
    """DuckQuerySession/RemoteDuckSession 同构替身：execute_df 返回 DataFrame

    按 SQL 前缀返回构造好的结果，模拟对账执行序列（DESCRIBE + checksum×2）。
    """

    describe_columns = ['target_id', 'i1', 'i2']
    parquet_rows = 2
    parquet_hash = 111
    pg_rows = 2
    pg_hash = 111

    def __enter__(self):
        import pandas as pd
        self._pd = pd
        return self

    def execute_df(self, sql: str):
        pd = self._pd
        if sql.startswith('DESCRIBE'):
            return pd.DataFrame({'column_name': self.describe_columns})
        # checksum: SELECT count(*), sum(hash(...)) FROM <relation>
        if 'read_parquet' in sql:
            return pd.DataFrame(
                {'count_star': [self.parquet_rows], 'checksum': [self.parquet_hash]})
        return pd.DataFrame({'count_star': [self.pg_rows], 'checksum': [self.pg_hash]})

    def __exit__(self, *args):
        return False


class TestReconcilePairViaSessionFactory:
    """Issue #2：对账统一经 get_query_session 工厂执行，不再触碰 DuckQuerySession.conn"""

    def _pair(self):
        d = date(2026, 9, 10)
        pg = types.SimpleNamespace(
            etl_date=d, parquet_file_path='cust_wide_table_abcdef12_20260910',
            storage_backend='postgresql')
        duck = types.SimpleNamespace(
            etl_date=d, parquet_file_path='/data/wt/cust_wide_table_abcdef12',
            storage_backend='duckdb')
        return pg, duck

    def test_reconcile_uses_session_factory_not_local_conn(self, monkeypatch):
        """对账经工厂注入的会话执行（remote 模式同路径，后端零 duckdb 依赖）"""
        job, qr = _load_reconcile_job(monkeypatch)
        created = []

        def fake_factory(attach_pg=True):
            session = _FakeDuckSession()
            created.append(session)
            return session

        qr.get_query_session = fake_factory

        pg, duck = self._pair()
        result = job._reconcile_pair(pg, duck)

        assert len(created) == 1  # 单次会话内完成 DESCRIBE + 双侧 checksum
        assert result['passed'] is True
        assert result['pg_rows'] == result['duck_rows'] == 2

    def test_reconcile_detects_row_mismatch(self, monkeypatch):
        job, qr = _load_reconcile_job(monkeypatch)

        class _Mismatch(_FakeDuckSession):
            parquet_rows = 2
            pg_rows = 3

        qr.get_query_session = lambda attach_pg=True: _Mismatch()
        pg, duck = self._pair()
        result = job._reconcile_pair(pg, duck)
        assert result['passed'] is False
        assert (result['pg_rows'], result['duck_rows']) == (3, 2)

    def test_reconcile_detects_checksum_mismatch(self, monkeypatch):
        job, qr = _load_reconcile_job(monkeypatch)

        class _BadHash(_FakeDuckSession):
            parquet_hash = 999

        qr.get_query_session = lambda attach_pg=True: _BadHash()
        pg, duck = self._pair()
        result = job._reconcile_pair(pg, duck)
        assert result['passed'] is False

    def test_reconcile_empty_tables_pass_with_none_hash(self, monkeypatch):
        """空表 sum(hash(...)) 为 NULL → None，双侧 None 判等通过"""
        job, qr = _load_reconcile_job(monkeypatch)

        class _Empty(_FakeDuckSession):
            parquet_rows = 0
            parquet_hash = None
            pg_rows = 0
            pg_hash = None

        qr.get_query_session = lambda attach_pg=True: _Empty()
        pg, duck = self._pair()
        result = job._reconcile_pair(pg, duck)
        assert result['passed'] is True
        assert result['pg_hash'] is None and result['duck_hash'] is None
