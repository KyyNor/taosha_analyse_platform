"""真实 ORM/实时加工调用链：等待线程时释放读会话，线程只在写快照时开会话。"""

import os
from pathlib import Path
import subprocess
import sys

import pytest


_ROOT = Path(__file__).resolve().parents[4]

# 在子进程隔离 services 包初始化与 SQLite 会话配置，复用 PG 基准的边界替身。
_SCENARIO = r'''
import importlib.util
from contextlib import contextmanager
from datetime import date, datetime
from threading import Event, local, current_thread, main_thread
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path
import sys

root = Path(sys.argv[1])
duckdb_mode = sys.argv[2] == 'duckdb'
fail_snapshot = sys.argv[3] == 'fail'
spec = importlib.util.spec_from_file_location(
    'session_test_harness', root / 'tests/backend/modules/pg_golden/harness.py',
)
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)
import services
import models.db_base as db_base
from services.scheduler.jobs import realtime_indicator_job as job
from services.fraudhunter.wide_table_service.store import query_router

h.install_sqlite()
pg = h.FakePG()
h.install_fake_pg(pg)
pg.fetch_handlers.append((lambda sql: 'realtime_oss_inct_new' in sql, h._realtime_task_df_factory))
with db_base.get_db_session() as db:
    h.seed_common(db)
    h.seed_version(db, 'dep_acct_wide_table', h.VH_DEP_OLD, h.dep_metadata(), 'current', datetime(2026, 9, 1))
    h.seed_version(db, 'cust_wide_table', h.VH_CUST, h.cust_metadata(), 'current', datetime(2026, 9, 1))
    h.seed_snapshot(db, 'dep_acct_wide_table', h.VH_DEP_OLD, date(2026, 10, 9), 'dep')
    h.seed_snapshot(db, 'cust_wide_table', h.VH_CUST, date(2026, 10, 9), 'cust')

read_closed = Event()
thread_state = local()
checks = []
original_session = db_base.get_db_session

@contextmanager
def tracked_session():
    thread_state.depth = getattr(thread_state, 'depth', 0) + 1
    try:
        with original_session() as db:
            yield db
    finally:
        thread_state.depth -= 1
        if current_thread() is main_thread():
            read_closed.set()

original_execute = job._execute_single_task
original_process = job._process_single_object_type
original_update = job._update_realtime_snapshot
original_resolve = job._resolve_offline_tables

def execute(*args):
    # 推迟 SQL 到读会话 commit/close 之后，稳定复现 ORM 过期竞态。
    assert read_closed.wait(3), 'step1 waited for workers while holding the read session'
    assert getattr(thread_state, 'depth', 0) == 0, 'worker SQL holds a metadata session'
    assert isinstance(args[0], SimpleNamespace), 'worker received an ORM task'
    assert args[-1] is duckdb_mode, 'DuckDB routing flag was lost during merge'
    checks.append('sql')
    return original_execute(*args)

def process(*args):
    assert isinstance(args[4], SimpleNamespace), 'worker received an ORM version'
    return original_process(*args)

def update(*args):
    assert getattr(thread_state, 'depth', 0) == 1, 'snapshot write has no session'
    checks.append('snapshot')
    if fail_snapshot:
        raise RuntimeError('snapshot write failed')
    return original_update(*args)

def resolve(*args):
    refs, mode = original_resolve(*args)
    assert mode is False
    return refs, duckdb_mode

@contextmanager
def duck_session(attach_pg=True):
    assert attach_pg is True
    yield SimpleNamespace(execute_df=lambda sql: pg.fetch_df(sql, {}))

with patch.object(db_base, 'get_db_session', tracked_session), \
     patch.object(job, 'get_db_session', tracked_session), \
     patch.object(job, '_execute_single_task', execute), \
     patch.object(job, '_process_single_object_type', process), \
     patch.object(job, '_update_realtime_snapshot', update), \
     patch.object(job, '_resolve_offline_tables', resolve), \
     patch.object(query_router, 'get_query_session', duck_session):
    result = job.step1_generate_realtime_indicators(h.TODAY, '2026-10-10', h.NOW_STR)

assert read_closed.is_set()
assert checks.count('sql') == 2
assert checks.count('snapshot') == 2
if fail_snapshot:
    assert result == (None, False, None)
else:
    refs, mode, generated = result
    assert mode is duckdb_mode
    assert set(generated) == {'dep_acct_no', 'cust_no'}
    assert all(name.endswith('_202610101430') for name in generated.values())
print('session lifetime and routing verified')
'''


@pytest.mark.parametrize("mode,failure", [("postgresql", "ok"), ("duckdb", "ok"), ("postgresql", "fail")])
def test_realtime_session_lifetime(mode, failure):
    env = {
        **os.environ,
        "TAOSHA_CONFIG_FILE": str(_ROOT / "tests/backend/modules/pg_golden/config.golden.yaml"),
        "PYTHONPATH": str(_ROOT / "backend"),
    }
    proc = subprocess.run(
        [sys.executable, "-c", _SCENARIO, str(_ROOT), mode, failure],
        cwd=_ROOT / "backend", env=env, capture_output=True, text=True, timeout=30,
    )
    assert proc.returncode == 0, "\n".join((proc.stdout + proc.stderr).splitlines()[-50:])
