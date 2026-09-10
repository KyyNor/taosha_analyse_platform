"""
DuckDB 远程计算模式（docs/duckdb_remote_compute_plan.md 阶段2/3）

覆盖:
- rewrite_path_in_sql: 后端路径 → 容器路径前缀重写
- RemoteDuckSession._to_dataframe: 列式 JSON → DataFrame（dtype 还原）
- query_router.get_query_session 工厂: local/remote 模式分发
- DuckdbParquetStore remote 写路径: pg 别名 pg_rt、分段写协议调用序列、
  对账断言共用（成功/失败清理）、SQL builder 别名参数化
"""

import importlib.util
import sys
import types
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

_backend_root = Path(__file__).parents[4] / "backend"
sys.path.insert(0, str(_backend_root))

ETL = date(2026, 9, 10)

MODE_LOCAL = types.SimpleNamespace(fraudhunter_duck_compute_mode='local')
MODE_REMOTE = types.SimpleNamespace(fraudhunter_duck_compute_mode='remote')


def _fake_settings(mode):
    return types.SimpleNamespace(
        fraudhunter_duck_compute_mode=mode,
        fraudhunter_duck_compute_endpoint='http://127.0.0.1:9495',
        fraudhunter_duck_compute_token='tok',
        fraudhunter_duck_compute_path_map={'/backend/data': '/container/data'},
        fraudhunter_duck_compute_timeout_seconds=300,
        fraudhunter_wide_table_duckdb_storage_path='/tmp/wt',
        fraudhunter_wide_table_duckdb_compression='zstd',
        fraudhunter_analyze_db={'postgresql': {
            'host': '127.0.0.1', 'port': 5432, 'database': 'd',
            'user': 'u', 'password': 'p',
        }},
    )


def _load_module(monkeypatch, rel_path, mod_name, settings_ns):
    """按分支惯例以 importlib 加载 backend 模块, 并注入 fake settings/logger"""
    for name in (
        'services', 'services.fraudhunter', 'services.fraudhunter.wide_table_service',
        'services.fraudhunter.wide_table_service.store', 'utils',
    ):
        monkeypatch.setitem(sys.modules, name, sys.modules.get(name) or types.ModuleType(name))

    config_module = types.ModuleType('utils.config')
    config_module.settings = settings_ns
    monkeypatch.setitem(sys.modules, 'utils.config', config_module)

    logger_module = types.ModuleType('utils.logger')
    logger_module.logger = types.SimpleNamespace(
        debug=lambda *a, **k: None, info=lambda *a, **k: None,
        warning=lambda *a, **k: None, error=lambda *a, **k: None,
    )
    monkeypatch.setitem(sys.modules, 'utils.logger', logger_module)

    # store 包依赖链: base/pg_store/analyze_db_utils
    analyze_module = types.ModuleType('utils.analyze_db_utils')
    analyze_module.AnalyzeDBPartitionManager = types.SimpleNamespace(drop_table=lambda t: None)
    monkeypatch.setitem(sys.modules, 'utils.analyze_db_utils', analyze_module)

    base_module = types.ModuleType('services.fraudhunter.wide_table_service.store.base')
    base_module.WideTableStore = type('WideTableStore', (), {})
    monkeypatch.setitem(
        sys.modules, 'services.fraudhunter.wide_table_service.store.base', base_module)

    pg_store_module = types.ModuleType('services.fraudhunter.wide_table_service.store.pg_store')
    pg_store_module.PgWideTableStore = type('PgWideTableStore', (), {})
    monkeypatch.setitem(
        sys.modules, 'services.fraudhunter.wide_table_service.store.pg_store', pg_store_module)

    spec = importlib.util.spec_from_file_location(mod_name, _backend_root / rel_path)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, mod_name, module)
    spec.loader.exec_module(module)
    return module


def _load_remote_session(monkeypatch, mode='remote'):
    return _load_module(
        monkeypatch,
        'services/fraudhunter/wide_table_service/store/remote_session.py',
        'services.fraudhunter.wide_table_service.store.remote_session',
        _fake_settings(mode),
    )


def _load_store(monkeypatch, mode):
    return _load_module(
        monkeypatch,
        'services/fraudhunter/wide_table_service/store/duckdb_parquet_store.py',
        'services.fraudhunter.wide_table_service.store.duckdb_parquet_store',
        _fake_settings(mode),
    )


class TestRewritePath:
    def test_prefix_rewritten(self, monkeypatch):
        rs = _load_remote_session(monkeypatch)
        sql = ("SELECT * FROM read_parquet('/backend/data/wt/etl_date=2026-09-10/*.parquet', "
               "hive_partitioning=false)")
        out = rs.rewrite_path_in_sql(sql, {'/backend/data': '/container/data'})
        assert '/container/data/wt/etl_date=' in out

    def test_no_map_noop(self, monkeypatch):
        rs = _load_remote_session(monkeypatch)
        sql = "SELECT count(*) FROM read_parquet('/same/path')"
        assert rs.rewrite_path_in_sql(sql, {}) == sql


class TestToDataFrame:
    def test_dtypes_restored(self, monkeypatch):
        rs = _load_remote_session(monkeypatch)
        payload = {
            'columns': ['i', 'f', 's', 'b'],
            'types': ['BIGINT', 'DOUBLE', 'VARCHAR', 'BOOLEAN'],
            'data': {'i': [1, 2], 'f': [1.5, None], 's': ['a', 'b'], 'b': [True, False]},
            'row_count': 2,
            'truncated': False,
        }
        df = rs.RemoteDuckSession._to_dataframe(payload)
        assert str(df['i'].dtype) == 'int64'
        assert str(df['f'].dtype) == 'float64'
        assert df['s'].tolist() == ['a', 'b']
        assert df['b'].tolist() == [True, False]

    def test_empty_result(self, monkeypatch):
        rs = _load_remote_session(monkeypatch)
        df = rs.RemoteDuckSession._to_dataframe(
            {'columns': ['i'], 'types': ['BIGINT'], 'data': {'i': []}, 'row_count': 0,
             'truncated': False})
        assert isinstance(df, pd.DataFrame) and len(df) == 0


class TestSessionFactory:
    def test_local_default(self, monkeypatch):
        qr = _load_module(
            monkeypatch,
            'services/fraudhunter/wide_table_service/store/query_router.py',
            'services.fraudhunter.wide_table_service.store.query_router',
            _fake_settings('local'),
        )
        with qr.get_query_session(attach_pg=False) as session:
            assert type(session).__name__ == 'DuckQuerySession'

    def test_remote_dispatch(self, monkeypatch):
        # 预加载 remote_session 到 sys.modules (fake 的 store 父模块不是真包,
        # 工厂内的惰性 from-import 依赖 sys.modules 命中)
        _load_remote_session(monkeypatch)
        qr = _load_module(
            monkeypatch,
            'services/fraudhunter/wide_table_service/store/query_router.py',
            'services.fraudhunter.wide_table_service.store.query_router',
            _fake_settings('remote'),
        )
        session = qr.get_query_session(attach_pg=True)
        assert type(session).__name__ == 'RemoteDuckSession'


class TestStoreRemote:
    def _store_with_mock_remote(self, monkeypatch):
        store_mod = _load_store(monkeypatch, 'remote')
        store = store_mod.DuckdbParquetStore()
        remote = MagicMock()
        monkeypatch.setattr(
            store_mod.DuckdbParquetStore, '_remote',
            staticmethod(lambda: remote))
        return store, store_mod, remote

    def test_pg_alias(self, monkeypatch):
        store_local = _load_store(monkeypatch, 'local').DuckdbParquetStore()
        assert store_local._pg_alias() == 'pg_src'
        store_remote = _load_store(monkeypatch, 'remote').DuckdbParquetStore()
        assert store_remote._pg_alias() == 'pg_rt'

    def test_build_copy_sql_alias(self, monkeypatch):
        store_mod = _load_store(monkeypatch, 'local')
        store = store_mod.DuckdbParquetStore()
        sql = store._build_copy_sql('t_staging', Path('/tmp/x'), alias='pg_rt')
        assert 'FROM pg_rt.public.t_staging' in sql
        # 默认值保持既有行为 (local 单测兼容)
        assert 'pg_src' in store._build_copy_sql('t', Path('/tmp/x'))

    def test_write_pivot_remote_happy_path(self, monkeypatch):
        store, store_mod, remote = self._store_with_mock_remote(monkeypatch)
        final_dir = Path('/data/wt_x/etl_date=2026-09-10')

        # 段1: COPY; 段2: DESCRIBE×2; 段3: checksum×2; 段4: land
        remote.remote_write_sqls.side_effect = [
            {'results': [{'rows': []}]},                                   # COPY
            {'results': [{'rows': [('i',), ('s',)]},                       # describe parquet
                         {'rows': [('i',), ('s',), ('created_at',)]}]},    # describe staging
            {'results': [{'rows': [(2, 111)]}, {'rows': [(2, 111)]}]},     # checksums
        ]
        remote.remote_write_land.return_value = {'files': ['f'], 'size_bytes': 99}

        store._write_pivot_remote('t_staging', final_dir, spark_rows=2)

        # COPY SQL 用 pg_rt 别名 + tmp 目录命名约定
        first_sqls = remote.remote_write_sqls.call_args_list[0].kwargs.get('sqls') \
            or remote.remote_write_sqls.call_args_list[0].args[0]
        assert 'FROM pg_rt.public.t_staging' in first_sqls[0]
        assert '/data/wt_x/etl_date=2026-09-10.tmp' in first_sqls[0]
        remote.remote_write_land.assert_called_once()
        remote.remote_write_cleanup.assert_not_called()

    def test_write_pivot_remote_reconcile_fail_cleans_tmp(self, monkeypatch):
        store, store_mod, remote = self._store_with_mock_remote(monkeypatch)
        final_dir = Path('/data/wt_x/etl_date=2026-09-10')
        remote.remote_write_sqls.side_effect = [
            {'results': [{'rows': []}]},
            {'results': [{'rows': [('i',)]}, {'rows': [('i',)]}]},
            # 行数不一致: staging=2, parquet=1
            {'results': [{'rows': [(1, 111)]}, {'rows': [(2, 111)]}]},
        ]
        with pytest.raises(RuntimeError, match='对账失败'):
            store._write_pivot_remote('t_staging', final_dir, spark_rows=2)
        remote.remote_write_cleanup.assert_called_once_with(
            '/data/wt_x/etl_date=2026-09-10.tmp')

    def test_merge_delta_remote_count_mismatch(self, monkeypatch):
        store, store_mod, remote = self._store_with_mock_remote(monkeypatch)
        remote.remote_write_sqls.return_value = {
            'results': [{'rows': []}, {'rows': [(10,)]}, {'rows': [(9,)]}],
        }
        with pytest.raises(RuntimeError, match='增量对账失败'):
            store._merge_delta_remote('COPY ...', 'read_parquet(...)',
                                      Path('/tmp/t'), Path('/tmp/f'))
        remote.remote_write_cleanup.assert_called_once()

    def test_merge_delta_remote_ok(self, monkeypatch):
        store, store_mod, remote = self._store_with_mock_remote(monkeypatch)
        remote.remote_write_sqls.return_value = {
            'results': [{'rows': []}, {'rows': [(10,)]}, {'rows': [(10,)]}],
        }
        remote.remote_write_land.return_value = {'files': ['f'], 'size_bytes': 5}
        n = store._merge_delta_remote('COPY ...', 'read_parquet(...)',
                                      Path('/tmp/t'), Path('/tmp/f'))
        assert n == 10
        remote.remote_write_cleanup.assert_not_called()

    def test_pull_pg_partition_remote(self, monkeypatch):
        store, store_mod, remote = self._store_with_mock_remote(monkeypatch)
        dest = Path('/data/wt/etl_date=2026-09-10')
        remote.remote_write_sqls.side_effect = [
            # COPY + source count
            {'results': [{'rows': []}, {'rows': [(5,)]}]},
            # describe×2 + checksum×2 (经 _remote_reconcile)
            {'results': [{'rows': [('a',), ('b',)]}, {'rows': [('a',), ('b',)]}]},
            {'results': [{'rows': [(5, 77)]}, {'rows': [(5, 77)]}]},
            # describe parquet (列数)
            {'results': [{'rows': [('a',), ('b',)]}]},
        ]
        remote.remote_write_land.return_value = {'files': ['f'], 'size_bytes': 123}

        rows, cols, size = store._pull_pg_partition_remote(
            'pg_t', ETL, dest, 'pg_rt', '(SELECT ...)')

        assert (rows, cols, size) == (5, 2, 123)
        # COPY SQL 分区日期下推 + pg_rt
        first_call = remote.remote_write_sqls.call_args_list[0]
        sqls = first_call.kwargs.get('sqls') or first_call.args[0]
        assert 'pg_rt.public.pg_t' in sqls[0]

    def test_push_parquet_to_pg_rejects_remote(self, monkeypatch):
        store, store_mod, remote = self._store_with_mock_remote(monkeypatch)
        with pytest.raises(RuntimeError, match='remote'):
            store.push_parquet_to_pg(Path('/v'), ETL, 'pg_t', {})

    def test_assert_reconcile_shared_rules(self, monkeypatch):
        store_mod = _load_store(monkeypatch, 'local')
        f = store_mod.DuckdbParquetStore._assert_reconcile
        # 一致 → 通过
        f(['a'], ['a'], 2, 7, 2, 7, 2)
        # spark 行数不符
        with pytest.raises(RuntimeError, match='Spark行数'):
            f(['a'], ['a'], 2, 7, 2, 7, 3)
        # 行数守恒破坏
        with pytest.raises(RuntimeError, match='行数'):
            f(['a'], ['a'], 2, 7, 3, 7, None)
        # checksum 不一致
        with pytest.raises(RuntimeError, match='校验和'):
            f(['a'], ['a'], 2, 7, 2, 8, None)
        # parquet 多列
        with pytest.raises(RuntimeError, match='多出'):
            f(['a', 'x'], ['a'], 1, 7, 1, 7, None)
