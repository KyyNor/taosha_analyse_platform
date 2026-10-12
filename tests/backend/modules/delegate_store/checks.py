"""delegate 模式与淘沙内部存储接口的检查集（docs/fraudhunter_offline_dual_store_plan.md 阶段 10）

在独立子进程中运行（真实 import 链 + 测试配置），逐项执行 check_* 函数，
结果以 JSON 输出 {检查名: "ok" | 失败信息}，由 test_delegate_store.py 逐项断言。

用法：python checks.py --out <结果.json>
"""

import argparse
import builtins
import json
import os
import shutil
import sys
import tempfile
import traceback
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
TESTS_MODULES = HERE.parent
BACKEND = TESTS_MODULES.parents[2] / "backend"
CONFIG = TESTS_MODULES / "pg_golden" / "config.golden.yaml"

os.environ["TAOSHA_CONFIG_FILE"] = str(CONFIG)
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(TESTS_MODULES / "pg_golden"))
os.chdir(BACKEND)

import services  # noqa: E402,F401  按应用顺序初始化包
from utils.config import settings  # noqa: E402

ETL = date(2026, 10, 9)


# =============================================================================
# 公共替身
# =============================================================================

class FakeStore:
    """ParquetOpsService 依赖的 DuckdbParquetStore 替身（记录调用）"""

    def __init__(self, storage_path):
        self._storage_path = Path(storage_path)
        self.calls = []
        self.raise_on = {}

    def _duck_compute_mode(self):
        return 'local'

    def _maybe_raise(self, name):
        if name in self.raise_on:
            raise self.raise_on[name]

    def probe_parquet(self, version_dir, etl_date):
        self.calls.append(('probe_parquet', version_dir, etl_date))
        return {'exists': True, 'rows': 42, 'error': None, 'version_dir': version_dir}

    def land_staging_to_parquet(self, staging, final_dir, spark_rows):
        self.calls.append(('land_staging_to_parquet', staging, str(final_dir), spark_rows))
        self._maybe_raise('land')
        return 1234

    def pull_pg_partition_to_parquet(self, pg_table, etl_date, dest_dir, expected_rows=None):
        self.calls.append(('pull_pg_partition_to_parquet', pg_table, etl_date, str(dest_dir), expected_rows))
        self._maybe_raise('partition')
        return (expected_rows or 7, 9, 555)

    def merge_delta_insert_select(self, **kwargs):
        self.calls.append(('merge_delta_insert_select', kwargs))
        self._maybe_raise('merge')
        return 77


def _ops(tmp):
    from services.fraudhunter.wide_table_service.store.parquet_ops import ParquetOpsService
    store = FakeStore(tmp)
    return ParquetOpsService(store=store), store


def _expect_ops_error(code, fn):
    from services.fraudhunter.wide_table_service.store.parquet_ops import ParquetOpsError
    try:
        fn()
    except ParquetOpsError as e:
        assert e.error_code == code, f"期望 {code}，实际 {e.error_code}: {e.message}"
        return e
    raise AssertionError(f"期望抛出 {code}")


# =============================================================================
# 服务端：ParquetOpsService
# =============================================================================

def check_ops_rejects_invalid_names(tmp):
    ops, store = _ops(tmp)
    for bad in ('../etc', 'A_upper', 'a/b', 'a.b', '', 'x' * 129, None):
        _expect_ops_error('INVALID_ARGUMENT', lambda b=bad: ops.probe(b, ETL))
    _expect_ops_error('INVALID_ARGUMENT', lambda: ops.pull('t;drop', 'staging', 'wt_1a2b3c4d', ETL, 3))
    _expect_ops_error('INVALID_ARGUMENT', lambda: ops.pull('t', 'sql', 'wt_1a2b3c4d', ETL, 3))
    _expect_ops_error('INVALID_ARGUMENT', lambda: ops.pull('t', 'staging', 'wt_1a2b3c4d', ETL, -1))
    (Path(tmp) / 'wt_old').mkdir()
    _expect_ops_error('INVALID_ARGUMENT', lambda: ops.merge(
        'wt_old', 'wt_new', ETL, 'd', ['ok_col'], ['bad-col']))
    assert store.calls == [], store.calls


def check_ops_probe_uses_server_storage_path(tmp):
    ops, store = _ops(tmp)
    res = ops.probe('dep_acct_wide_table_1a2b3c4d', ETL)
    expected = str(Path(tmp).resolve() / 'dep_acct_wide_table_1a2b3c4d')
    assert res['version_dir'] == expected, res
    assert store.calls == [('probe_parquet', expected, ETL)]


def check_ops_pull_staging_and_partition(tmp):
    ops, store = _ops(tmp)
    res = ops.pull('_staging_wt_1a2b3c4d_20261009', 'staging', 'wt_1a2b3c4d', ETL, 3)
    vdir = Path(tmp).resolve() / 'wt_1a2b3c4d'
    assert res == {'rows': 3, 'column_count': None, 'size_bytes': 1234,
                   'final_dir': str(vdir / 'etl_date=2026-10-09'), 'version_dir': str(vdir)}, res
    res = ops.pull('wt_1a2b3c4d_20261009', 'partition', 'wt_1a2b3c4d', ETL, 120)
    assert res['rows'] == 120 and res['column_count'] == 9 and res['size_bytes'] == 555, res
    assert store.calls[1] == ('pull_pg_partition_to_parquet', 'wt_1a2b3c4d_20261009', ETL,
                              str(vdir / 'etl_date=2026-10-09'), 120), store.calls


def check_ops_translates_store_errors(tmp):
    from services.fraudhunter.wide_table_service.store.duckdb_parquet_store import (
        ReconcileError, TargetUniverseChangedError,
    )
    ops, store = _ops(tmp)
    store.raise_on['land'] = ReconcileError('rows mismatch')
    _expect_ops_error('RECONCILE_FAILED', lambda: ops.pull('stg', 'staging', 'wt_x', ETL, 3))
    (Path(tmp) / 'wt_old').mkdir()
    store.raise_on['merge'] = TargetUniverseChangedError('new ids')
    _expect_ops_error('TARGET_UNIVERSE_CHANGED', lambda: ops.merge(
        'wt_old', 'wt_new', ETL, '_delta_wt_new_20261009', ['a'], ['b']))
    store.raise_on['merge'] = ValueError('boom')
    try:
        ops.merge('wt_old', 'wt_new', ETL, None, ['a'], [])
        raise AssertionError('未知异常应原样抛出')
    except ValueError:
        pass


def check_ops_merge_requires_base_dir(tmp):
    ops, store = _ops(tmp)
    _expect_ops_error('NOT_FOUND', lambda: ops.merge('wt_missing', 'wt_new', ETL, None, ['a'], []))
    (Path(tmp) / 'wt_old').mkdir()
    res = ops.merge('wt_old', 'wt_new', ETL, '_delta_wt_new_20261009', ['a'], ['b'])
    kwargs = store.calls[-1][1]
    assert kwargs['base_table'] == str((Path(tmp) / 'wt_old').resolve()), kwargs
    assert kwargs['dest_table'] == 'wt_new' and kwargs['etl_date'] == '2026-10-09', kwargs
    assert res['rows'] == 77 and res['version_dir'].endswith('/wt_new'), res


def check_ops_lock_conflict_busy(tmp):
    import fcntl
    ops, store = _ops(tmp)
    with ops._target_lock('wt_x', ETL):
        _expect_ops_error('BUSY', lambda: ops.pull('stg', 'staging', 'wt_x', ETL, 3))
        # 不同日期互不影响
        ops.pull('stg', 'staging', 'wt_x', date(2026, 10, 8), 3)
    # 锁释放后可再次获取
    ops.pull('stg', 'staging', 'wt_x', ETL, 3)
    assert fcntl  # noqa


def check_ops_cleanup_idempotent(tmp):
    ops, _ = _ops(tmp)
    tmp_dir = Path(tmp) / 'wt_x' / 'etl_date=2026-10-09.tmp'
    tmp_dir.mkdir(parents=True)
    (tmp_dir / 'part-00000.parquet').write_bytes(b'x')
    assert ops.cleanup('wt_x', ETL)['removed'] is True
    assert not tmp_dir.exists()
    assert ops.cleanup('wt_x', ETL)['removed'] is False


def check_ops_rejects_delegate_server_mode(tmp):
    from services.fraudhunter.wide_table_service.store.parquet_ops import ParquetOpsService
    old = settings.fraudhunter_duck_compute_mode
    settings.fraudhunter_duck_compute_mode = 'delegate'
    try:
        _expect_ops_error('NOT_CONFIGURED', lambda: ParquetOpsService())
    finally:
        settings.fraudhunter_duck_compute_mode = old


def check_ops_probe_real_parquet_local(tmp):
    """真实 DuckdbParquetStore（local）探测真实 Parquet 文件：存在/行数/缺失"""
    import duckdb
    from services.fraudhunter.wide_table_service.store.duckdb_parquet_store import DuckdbParquetStore
    from services.fraudhunter.wide_table_service.store.parquet_ops import ParquetOpsService

    settings.fraudhunter_wide_table_duckdb_storage_path = tmp
    settings.fraudhunter_duck_compute_mode = 'local'
    date_dir = Path(tmp) / 'wt_1a2b3c4d' / 'etl_date=2026-10-09'
    date_dir.mkdir(parents=True)
    duckdb.sql(
        "COPY (SELECT range::VARCHAR AS target_id FROM range(5)) "
        f"TO '{(date_dir / 'part-00000.parquet').as_posix()}' (FORMAT PARQUET)"
    )
    ops = ParquetOpsService()
    assert isinstance(ops.store, DuckdbParquetStore)
    res = ops.probe('wt_1a2b3c4d', ETL)
    assert res['exists'] is True and res['rows'] == 5 and res['error'] is None, res
    res = ops.probe('wt_1a2b3c4d', date(2026, 10, 8))
    assert res['exists'] is False, res


# =============================================================================
# 服务端：路由（鉴权 + 错误码）
# =============================================================================

def _client(monkey_service):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from api.fraudhunter import internal_wide_table_store_routes as routes

    routes._service = lambda: monkey_service
    app = FastAPI()
    app.include_router(routes.router, prefix="/api/taosha/v1/fraudhunter")
    return TestClient(app)


URL = "/api/taosha/v1/fraudhunter/internal/wide-table-store/parquet"


def check_routes_token_guard(tmp):
    ops, _ = _ops(tmp)
    client = _client(ops)
    body = {'version_dir_name': 'wt_x', 'etl_date': '2026-10-09'}
    old = settings.fraudhunter_internal_api_token
    try:
        settings.fraudhunter_internal_api_token = ''
        r = client.post(f"{URL}/probe", json=body, headers={'X-Internal-Token': 'anything'})
        assert r.status_code == 503 and r.json()['detail']['error_code'] == 'NOT_CONFIGURED', r.text
        settings.fraudhunter_internal_api_token = 's3cret'
        r = client.post(f"{URL}/probe", json=body)
        assert r.status_code == 401 and r.json()['detail']['error_code'] == 'UNAUTHORIZED', r.text
        r = client.post(f"{URL}/probe", json=body, headers={'X-Internal-Token': 'wrong'})
        assert r.status_code == 401, r.text
        r = client.post(f"{URL}/probe", json=body, headers={'X-Internal-Token': 's3cret'})
        assert r.status_code == 200 and r.json()['rows'] == 42, r.text
    finally:
        settings.fraudhunter_internal_api_token = old


def check_routes_error_codes(tmp):
    from services.fraudhunter.wide_table_service.store.duckdb_parquet_store import ReconcileError
    ops, store = _ops(tmp)
    client = _client(ops)
    old = settings.fraudhunter_internal_api_token
    settings.fraudhunter_internal_api_token = 's3cret'
    h = {'X-Internal-Token': 's3cret'}
    try:
        r = client.post(f"{URL}/probe", json={'version_dir_name': '../x', 'etl_date': '2026-10-09'}, headers=h)
        assert r.status_code == 422 and r.json()['detail']['error_code'] == 'INVALID_ARGUMENT', r.text
        r = client.post(f"{URL}/probe", json={'version_dir_name': 'wt_x', 'etl_date': '20261009'}, headers=h)
        assert r.status_code == 422, r.text
        store.raise_on['land'] = ReconcileError('rows mismatch')
        r = client.post(f"{URL}/pull", headers=h, json={
            'source_pg_table': 'stg', 'source_kind': 'staging', 'version_dir_name': 'wt_x',
            'etl_date': '2026-10-09', 'expected_rows': 3})
        assert r.status_code == 422 and r.json()['detail']['error_code'] == 'RECONCILE_FAILED', r.text
        r = client.post(f"{URL}/merge", headers=h, json={
            'base_version_dir_name': 'wt_none', 'dest_version_dir_name': 'wt_new',
            'etl_date': '2026-10-09', 'static_cols': ['a']})
        assert r.status_code == 404 and r.json()['detail']['error_code'] == 'NOT_FOUND', r.text
        with ops._target_lock('wt_y', ETL):
            r = client.post(f"{URL}/pull", headers=h, json={
                'source_pg_table': 'stg', 'source_kind': 'staging', 'version_dir_name': 'wt_y',
                'etl_date': '2026-10-09', 'expected_rows': 3})
        assert r.status_code == 409 and r.json()['detail']['error_code'] == 'BUSY', r.text
    finally:
        settings.fraudhunter_internal_api_token = old


def check_routes_are_sync_def(tmp):
    """路由必须是同步 def（线程池执行），避免长时间 COPY 阻塞事件循环"""
    import inspect
    from api.fraudhunter import internal_wide_table_store_routes as routes
    for route in routes.router.routes:
        assert not inspect.iscoroutinefunction(route.endpoint), route.path


# =============================================================================
# DS 侧：delegate 客户端
# =============================================================================

class _Resp:
    def __init__(self, status, body):
        self.status_code, self._body, self.text = status, body, json.dumps(body)

    def json(self):
        return self._body


def _with_delegate_settings():
    settings.fraudhunter_duck_compute_delegate_endpoint = 'http://taosha:50011/'
    settings.fraudhunter_internal_api_token = 's3cret'


def check_client_busy_retry_and_headers(tmp):
    from services.fraudhunter.wide_table_service.store import delegate_client as dc
    _with_delegate_settings()
    sent = []
    responses = [
        _Resp(409, {'detail': {'error_code': 'BUSY', 'message': 'locked'}}),
        _Resp(200, {'rows': 3, 'final_dir': '/d/x', 'version_dir': '/d'}),
    ]

    def fake_post(url, json=None, headers=None, timeout=None):
        sent.append((url, json, headers, timeout))
        return responses.pop(0)

    orig_post, orig_sleep = dc.requests.post, dc.time.sleep
    dc.requests.post, dc.time.sleep = fake_post, lambda s: None
    try:
        res = dc.pull('stg', 'staging', 'wt_x', ETL, 3)
    finally:
        dc.requests.post, dc.time.sleep = orig_post, orig_sleep
    assert res['rows'] == 3
    assert len(sent) == 2
    url, body, headers, timeout = sent[0]
    assert url == 'http://taosha:50011/api/taosha/v1/fraudhunter/internal/wide-table-store/parquet/pull', url
    assert headers == {'X-Internal-Token': 's3cret'}, headers
    assert body == {'source_pg_table': 'stg', 'source_kind': 'staging', 'version_dir_name': 'wt_x',
                    'etl_date': '2026-10-09', 'expected_rows': 3}, body
    assert timeout == 1800.0, timeout


def check_client_error_mapping(tmp):
    from services.fraudhunter.wide_table_service.store import delegate_client as dc
    _with_delegate_settings()
    cases = [
        (_Resp(409, {'detail': {'error_code': 'TARGET_UNIVERSE_CHANGED', 'message': 'm'}}), 'TARGET_UNIVERSE_CHANGED'),
        (_Resp(401, {'detail': {'error_code': 'UNAUTHORIZED', 'message': 'm'}}), 'UNAUTHORIZED'),
        (_Resp(500, {'detail': 'oops'}), 'HTTP_500'),
    ]
    orig = dc.requests.post
    try:
        for resp, code in cases:
            dc.requests.post = lambda *a, r=resp, **k: r
            try:
                dc.probe('wt_x', ETL)
                raise AssertionError('应抛 DelegateError')
            except dc.DelegateError as e:
                assert e.error_code == code, (e.error_code, code)

        def unreachable(*a, **k):
            raise dc.requests.ConnectionError('refused')
        dc.requests.post = unreachable
        try:
            dc.probe('wt_x', ETL)
            raise AssertionError('应抛 DelegateError')
        except dc.DelegateError as e:
            assert e.error_code == 'UNREACHABLE'
    finally:
        dc.requests.post = orig
    settings.fraudhunter_duck_compute_delegate_endpoint = ''
    try:
        dc.probe('wt_x', ETL)
        raise AssertionError('未配置 endpoint 应失败')
    except dc.DelegateError as e:
        assert e.error_code == 'NOT_CONFIGURED'


# =============================================================================
# DS 侧：delegate 模式全链路同步（SQLite + FakePG + Spark 替身 + 内存版淘沙服务端）
# =============================================================================

class FsTouchError(AssertionError):
    pass


class forbid_local_fs:
    """delegate 模式下禁止访问本地文件系统与加载 duckdb"""

    def __enter__(self):
        import pathlib
        self._saved = {}

        def guard(name):
            def _f(*a, **k):
                raise FsTouchError(f"delegate 模式访问了本地文件系统: {name}{a[:2]}")
            return _f

        for attr in ('mkdir', 'glob', 'is_dir', 'exists', 'iterdir', 'rglob', 'stat', 'unlink', 'rmdir'):
            self._saved[('Path', attr)] = getattr(pathlib.Path, attr)
            setattr(pathlib.Path, attr, guard(f'Path.{attr}'))
        for mod, attr in ((shutil, 'rmtree'), (os, 'rename'), (os, 'makedirs')):
            self._saved[(mod, attr)] = getattr(mod, attr)
            setattr(mod, attr, guard(f'{mod.__name__}.{attr}'))
        self._duckdb = sys.modules.get('duckdb', '__absent__')
        sys.modules['duckdb'] = None
        from services.fraudhunter.wide_table_service.store import query_router
        self._gqs = query_router.get_query_session
        query_router.get_query_session = guard('query_router.get_query_session')
        return self

    def __exit__(self, *exc):
        import pathlib
        from services.fraudhunter.wide_table_service.store import query_router
        for (owner, attr), value in self._saved.items():
            setattr(pathlib.Path if owner == 'Path' else owner, attr, value)
        if self._duckdb == '__absent__':
            sys.modules.pop('duckdb', None)
        else:
            sys.modules['duckdb'] = self._duckdb
        query_router.get_query_session = self._gqs
        return False


class InMemoryServer:
    """淘沙服务端替身：模拟 storage_path 下的版本目录（不落真实文件）"""

    STORAGE = '/srv/taosha/parquet'

    def __init__(self):
        self.calls = []
        self.dirs = {}  # (version_dir_name, etl_date) -> rows
        self.universe_changed = False

    def _vdir(self, name):
        return f"{self.STORAGE}/{name}"

    def probe(self, version_dir_name, etl_date):
        self.calls.append(('probe', version_dir_name, etl_date))
        rows = self.dirs.get((version_dir_name, etl_date))
        return {'exists': rows is not None, 'rows': rows or 0, 'error': None,
                'version_dir': self._vdir(version_dir_name)}

    def pull(self, source_pg_table, source_kind, version_dir_name, etl_date, expected_rows=None):
        from services.fraudhunter.wide_table_service.store.delegate_client import DelegateError
        self.calls.append(('pull', source_pg_table, source_kind, version_dir_name, etl_date, expected_rows))
        if getattr(self, 'pull_error', None):
            raise DelegateError(self.pull_error, 'pull 失败（模拟）', 422)
        rows = expected_rows if expected_rows is not None else 50
        self.dirs[(version_dir_name, etl_date)] = rows
        return {'rows': rows, 'column_count': 7 if source_kind == 'partition' else None, 'size_bytes': 100,
                'final_dir': f"{self._vdir(version_dir_name)}/etl_date={etl_date}",
                'version_dir': self._vdir(version_dir_name)}

    def merge(self, base_version_dir_name, dest_version_dir_name, etl_date, delta_table,
              static_cols, inc_cols):
        from services.fraudhunter.wide_table_service.store.delegate_client import DelegateError
        self.calls.append(('merge', base_version_dir_name, dest_version_dir_name, etl_date,
                           delta_table, list(static_cols), list(inc_cols)))
        if self.universe_changed:
            raise DelegateError('TARGET_UNIVERSE_CHANGED', 'delta 含新 target_id', 409)
        rows = self.dirs[(base_version_dir_name, etl_date)]
        self.dirs[(dest_version_dir_name, etl_date)] = rows
        return {'rows': rows, 'size_bytes': 100,
                'final_dir': f"{self._vdir(dest_version_dir_name)}/etl_date={etl_date}",
                'version_dir': self._vdir(dest_version_dir_name)}


def _delegate_sync(scenario_setup, server, offline_store='duckdb', pg_tables=None):
    """以 delegate 模式运行 WideTableSyncService.sync_multi_dates，返回 (result, pg, engine)"""
    import harness as h
    from services.fraudhunter.wide_table_service.store import delegate_client as dc

    engine = h.install_sqlite()
    pg = h.FakePG()
    h.install_fake_pg(pg)
    h.install_fake_spark(pg)
    settings.pyspark_enabled = False
    settings.fraudhunter_wide_table_offline_store = offline_store
    settings.fraudhunter_duck_compute_mode = 'delegate'
    pg.tables.update(pg_tables or {})
    dc.probe, dc.pull, dc.merge = server.probe, server.pull, server.merge

    from models.db_base import get_db_session
    with get_db_session() as db:
        h.seed_common(db)
        scenario_setup(db, h)

    from services.fraudhunter.wide_table_service.sync_service import WideTableSyncService
    WideTableSyncService._calculate_etl_dates = lambda self, n: [ETL]
    with forbid_local_fs():
        service = WideTableSyncService()
        result = service.sync_multi_dates(wide_table_name='dep_acct_wide_table', lookback_days=1)
    return result, pg, engine


def _duck_snapshots(engine):
    from sqlalchemy import text
    with engine.connect() as conn:
        return [dict(r) for r in conn.execute(text(
            "SELECT version_hash, etl_date, parquet_file_path, row_count, status "
            "FROM fraudhunter_wide_table_snapshot WHERE storage_backend='duckdb' "
            "ORDER BY version_hash")).mappings()]


def _seed_old_duck_snapshot(db, h, vh=None, path=None):
    from models.fraudhunter.wide_table import FraudHunterWideTableSnapshot
    vh = vh or h.VH_DEP_OLD
    db.add(FraudHunterWideTableSnapshot(
        wide_table_name='dep_acct_wide_table', version_hash=vh, etl_date=ETL,
        parquet_file_path=path or f"{InMemoryServer.STORAGE}/dep_acct_wide_table_{vh}",
        row_count=120, column_count=7, status='ready', storage_backend='duckdb',
        generation_time=datetime(2026, 10, 9, 6, 0, 0),
    ))
    db.flush()


def _versions(db, h, old_codes, new_codes, bump=None):
    old_md = h.dep_metadata(include_realtime=False, codes=set(old_codes))
    new_md = h.dep_metadata(include_realtime=False, codes=set(new_codes))
    if bump:
        new_md[bump]['version'] = 2
    h.seed_version(db, 'dep_acct_wide_table', h.VH_DEP_OLD, old_md, 'current', datetime(2026, 9, 1))
    h.seed_version(db, 'dep_acct_wide_table', h.VH_DEP_NEW, new_md, 'target', datetime(2026, 10, 1))
    h._seed_progress(db, new_md, [ETL])


BASE = ['i_dep_acct_no_offline_00001', 'i_dep_acct_no_offline_00002', 'i_dep_acct_no_offline_00010']


def check_delegate_full_sync(tmp):
    server = InMemoryServer()

    def setup(db, h):
        md = h.dep_metadata(include_realtime=False)
        h.seed_version(db, 'dep_acct_wide_table', h.VH_DEP_NEW, md, 'target', datetime(2026, 10, 1))
        h._seed_progress(db, md, [ETL])

    result, pg, engine = _delegate_sync(setup, server)
    assert result['synced'] == 1, result
    assert [c[0] for c in server.calls] == ['pull'], server.calls
    _, src, kind, vname, d, rows = server.calls[0]
    assert (src, kind, vname, d, rows) == (
        '_staging_dep_acct_wide_table_5e6f7a8b_20261009', 'staging', 'dep_acct_wide_table_5e6f7a8b', ETL, 3)
    snaps = _duck_snapshots(engine)
    assert len(snaps) == 1 and snaps[0]['parquet_file_path'] == '/srv/taosha/parquet/dep_acct_wide_table_5e6f7a8b', snaps
    # staging 在 DS 侧（可访问 PG）建表、写入、成功后 DROP
    sqls = [e[1] for e in pg.events if e[0] == 'engine.execute']
    assert any('CREATE UNLOGGED TABLE IF NOT EXISTS _staging_dep_acct_wide_table_5e6f7a8b_20261009' in s for s in sqls)
    assert any(s.startswith('DROP TABLE IF EXISTS _staging_dep_acct_wide_table_5e6f7a8b_20261009') for s in sqls), sqls[-3:]


def check_delegate_delta_sync_uses_probe(tmp):
    """增量基准经服务端 probe 找到（不再因本地 glob 静默退化为全量）"""
    server = InMemoryServer()
    server.dirs[('dep_acct_wide_table_1a2b3c4d', ETL)] = 120

    def setup(db, h):
        _versions(db, h, BASE, BASE + ['i_dep_acct_no_offline_00012'], bump='4')
        _seed_old_duck_snapshot(db, h)

    result, pg, engine = _delegate_sync(setup, server)
    assert result['synced'] == 1, result
    kinds = [c[0] for c in server.calls]
    assert kinds == ['probe', 'merge'], server.calls
    merge = server.calls[1]
    assert merge[1:5] == ('dep_acct_wide_table_1a2b3c4d', 'dep_acct_wide_table_5e6f7a8b', ETL,
                          '_delta_dep_acct_wide_table_5e6f7a8b_20261009'), merge
    assert sorted(merge[5]) == ['i_dep_acct_no_offline_00001', 'i_dep_acct_no_offline_00002'], merge
    assert sorted(merge[6]) == ['i_dep_acct_no_offline_00010', 'i_dep_acct_no_offline_00012'], merge
    snaps = {s['version_hash']: s for s in _duck_snapshots(engine)}
    assert snaps['5e6f7a8b']['parquet_file_path'] == '/srv/taosha/parquet/dep_acct_wide_table_5e6f7a8b', snaps
    assert snaps['5e6f7a8b']['row_count'] == 120, snaps


def check_delegate_universe_changed_falls_back_to_full(tmp):
    server = InMemoryServer()
    server.dirs[('dep_acct_wide_table_1a2b3c4d', ETL)] = 120
    server.universe_changed = True

    def setup(db, h):
        _versions(db, h, BASE, BASE + ['i_dep_acct_no_offline_00012'])
        _seed_old_duck_snapshot(db, h)

    result, _, engine = _delegate_sync(setup, server)
    assert result['synced'] == 1, result
    assert [c[0] for c in server.calls] == ['probe', 'merge', 'pull'], server.calls
    assert server.calls[2][2] == 'staging', server.calls[2]


def check_delegate_zero_copy_when_unchanged(tmp):
    server = InMemoryServer()
    server.dirs[('dep_acct_wide_table_1a2b3c4d', ETL)] = 120

    def setup(db, h):
        _versions(db, h, BASE, BASE)
        _seed_old_duck_snapshot(db, h)

    result, pg, engine = _delegate_sync(setup, server)
    assert [c[0] for c in server.calls] == ['probe'], server.calls
    assert not any(e[0].startswith('spark') for e in pg.events), '零拷贝不应执行 Spark'
    snaps = {s['version_hash']: s for s in _duck_snapshots(engine)}
    assert snaps['5e6f7a8b']['parquet_file_path'] == '/srv/taosha/parquet/dep_acct_wide_table_1a2b3c4d', snaps


def check_delegate_probe_path_mismatch_not_reused(tmp):
    """快照记录路径与服务端 storage_path 不一致时不复用（防两侧配置漂移），回退全量"""
    server = InMemoryServer()
    server.dirs[('dep_acct_wide_table_1a2b3c4d', ETL)] = 120

    def setup(db, h):
        _versions(db, h, BASE, BASE + ['i_dep_acct_no_offline_00012'])
        _seed_old_duck_snapshot(db, h, path='/other/root/dep_acct_wide_table_1a2b3c4d')

    result, _, _ = _delegate_sync(setup, server)
    assert result['synced'] == 1, result
    assert [c[0] for c in server.calls] == ['probe', 'pull'], server.calls


# =============================================================================
# 阶段 11：both 模式 DuckDB 复用 PG 数据（只跑一次 Spark）
# =============================================================================

def _spark_pivots(pg):
    return [e for e in pg.events if e[0] == 'spark.query_sql' and 'PIVOT' in str(e[1])]


def _all_snapshots(engine):
    from sqlalchemy import text
    with engine.connect() as conn:
        return [dict(r) for r in conn.execute(text(
            "SELECT storage_backend, version_hash, parquet_file_path, row_count, status "
            "FROM fraudhunter_wide_table_snapshot WHERE version_hash='5e6f7a8b' "
            "ORDER BY storage_backend")).mappings()]


def _full_target_setup(db, h):
    md = h.dep_metadata(include_realtime=False)
    h.seed_version(db, 'dep_acct_wide_table', h.VH_DEP_NEW, md, 'target', datetime(2026, 10, 1))
    h._seed_progress(db, md, [ETL])


def check_both_full_spark_once(tmp):
    server = InMemoryServer()
    result, pg, engine = _delegate_sync(_full_target_setup, server, offline_store='both')
    assert result['synced'] == 1, result
    assert len(_spark_pivots(pg)) == 1, f"both 模式 Spark PIVOT 应只执行一次: {len(_spark_pivots(pg))}"
    assert server.calls == [('pull', 'dep_acct_wide_table_5e6f7a8b', 'partition',
                             'dep_acct_wide_table_5e6f7a8b', ETL, 3)], server.calls
    snaps = _all_snapshots(engine)
    assert [(x['storage_backend'], x['status'], x['row_count']) for x in snaps] == [
        ('duckdb', 'ready', 3), ('postgresql', 'ready', 3)], snaps
    assert snaps[0]['parquet_file_path'] == '/srv/taosha/parquet/dep_acct_wide_table_5e6f7a8b'
    # 没有创建 staging 表
    assert not any('_staging_' in str(e[1]) for e in pg.events), 'both 复用路径不应创建 staging'


def check_both_pg_failed_duckdb_falls_back_to_spark(tmp):
    from services.fraudhunter.wide_table_service.store.pg_store import PgWideTableStore
    server = InMemoryServer()
    original = PgWideTableStore.write_pivot

    def failing(self, sql, table_name, etl_date, refresh_sql=None):
        if not table_name.startswith('_staging_'):
            raise RuntimeError('PG 写入失败（模拟）')
        return original(self, sql, table_name, etl_date, refresh_sql)

    PgWideTableStore.write_pivot = failing
    try:
        result, pg, engine = _delegate_sync(_full_target_setup, server, offline_store='both')
    finally:
        PgWideTableStore.write_pivot = original
    assert result['synced'] == 1, result
    assert [c[2] for c in server.calls] == ['staging'], server.calls
    snaps = {x['storage_backend']: x for x in _all_snapshots(engine)}
    assert snaps['postgresql']['status'] == 'failed' and snaps['duckdb']['status'] == 'ready', snaps


def check_both_pull_reconcile_failure_marks_duckdb_failed(tmp):
    server = InMemoryServer()
    server.pull_error = 'RECONCILE_FAILED'
    result, pg, engine = _delegate_sync(_full_target_setup, server, offline_store='both')
    assert result['synced'] == 1, result  # PG 成功即本日期成功
    snaps = {x['storage_backend']: x for x in _all_snapshots(engine)}
    assert snaps['postgresql']['status'] == 'ready' and snaps['duckdb']['status'] == 'failed', snaps
    assert len(_spark_pivots(pg)) == 1, '对账失败不应静默改跑 Spark'


def check_both_unchanged_pulls_reusable_pg_partition(tmp):
    """PG 因版本无变化跳过、DuckDB 无旧 Parquet：从 PG 可复用旧分区拉取"""
    server = InMemoryServer()

    def setup(db, h):
        _versions(db, h, BASE, BASE)
        h.seed_snapshot(db, 'dep_acct_wide_table', h.VH_DEP_OLD, ETL, 'dep_acct_wide_table_1a2b3c4d')

    result, pg, engine = _delegate_sync(
        setup, server, offline_store='both',
        pg_tables={'dep_acct_wide_table_1a2b3c4d_20261009': 80},
    )
    assert not _spark_pivots(pg), 'PG 跳过 + 复用旧分区时不应执行 Spark'
    assert server.calls == [('pull', 'dep_acct_wide_table_1a2b3c4d_20261009', 'partition',
                             'dep_acct_wide_table_5e6f7a8b', ETL, None)], server.calls
    snaps = {x['storage_backend']: x for x in _all_snapshots(engine)}
    assert snaps['duckdb']['status'] == 'ready' and 'postgresql' not in snaps, snaps


def check_both_existing_pg_snapshot_reused(tmp):
    """PG 本版本快照已存在（上一轮已同步）、DuckDB 尚无：DuckDB 拉取 PG 本版本表"""
    server = InMemoryServer()

    def setup(db, h):
        _full_target_setup(db, h)
        h.seed_snapshot(db, 'dep_acct_wide_table', h.VH_DEP_NEW, ETL, 'dep_acct_wide_table_5e6f7a8b', rows=321)

    result, pg, engine = _delegate_sync(setup, server, offline_store='both')
    assert not _spark_pivots(pg)
    assert server.calls == [('pull', 'dep_acct_wide_table_5e6f7a8b', 'partition',
                             'dep_acct_wide_table_5e6f7a8b', ETL, 321)], server.calls


def check_both_duckdb_zero_copy_preferred(tmp):
    """DuckDB 有旧版本 Parquet 且版本无变化：零拷贝优先于从 PG 拉取"""
    server = InMemoryServer()
    server.dirs[('dep_acct_wide_table_1a2b3c4d', ETL)] = 120

    def setup(db, h):
        _versions(db, h, BASE, BASE)
        h.seed_snapshot(db, 'dep_acct_wide_table', h.VH_DEP_OLD, ETL, 'dep_acct_wide_table_1a2b3c4d')
        _seed_old_duck_snapshot(db, h)

    result, pg, engine = _delegate_sync(
        setup, server, offline_store='both',
        pg_tables={'dep_acct_wide_table_1a2b3c4d_20261009': 120},
    )
    assert [c[0] for c in server.calls] == ['probe'], server.calls


# =============================================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True)
    args = parser.parse_args()

    checks = {k: v for k, v in globals().items() if k.startswith('check_') and callable(v)}
    results = {}
    snapshot = {k: getattr(settings, k) for k in dir(settings) if k.startswith(('fraudhunter_', 'pyspark_'))}
    for name, fn in checks.items():
        tmp = tempfile.mkdtemp(prefix='delegate_check_')
        try:
            fn(tmp)
            results[name] = 'ok'
        except BaseException:  # noqa: BLE001 - 汇总报告
            results[name] = traceback.format_exc()
        finally:
            for k, v in snapshot.items():
                try:
                    setattr(settings, k, v)
                except Exception:
                    pass
            shutil.rmtree(tmp, ignore_errors=True)
    Path(args.out).write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding='utf-8')


if __name__ == '__main__':
    builtins  # noqa
    main()
