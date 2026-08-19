"""
阶段4：查询路由与方言适配 —— SqlDialect / query_router / DuckQuerySession

对应 docs/fraudhunter_offline_dual_store_plan.md 阶段4：
- SqlDialect 双方言原语输出（正则/CAST/quote）；
- 表引用路由：duckdb 快照 → read_parquet glob；postgresql 快照 → PG分区名（现状公式）；
  duckdb 执行模式下 PG 侧表带 pg_rt 前缀；
- DuckQuerySession 纯本地 Parquet 查询（attach_pg=False）端到端；
- rule_engine 的 dialect 参数（PG 默认零变化 + duckdb 正则改写）。
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

ETL = date(2026, 8, 19)


def _make_fake_snapshot(backend='postgresql', parquet_path='cust_wide_table_abcd1234',
                        wide_table='cust_wide_table', version_hash='abcd1234efgh' * 4):
    return types.SimpleNamespace(
        wide_table_name=wide_table,
        version_hash=version_hash,
        parquet_file_path=parquet_path,
        etl_date=ETL,
        storage_backend=backend,
    )


def _load_query_router(monkeypatch):
    services_module = types.ModuleType("services")
    fraudhunter_module = types.ModuleType("services.fraudhunter")
    wide_table_service_module = types.ModuleType("services.fraudhunter.wide_table_service")

    config_module = types.ModuleType("utils.config")
    config_module.settings = types.SimpleNamespace(
        fraudhunter_analyze_db={"postgresql": {
            "host": "127.0.0.1", "port": 5432, "database": "taosha_fraudhunter",
            "user": "taosha", "password": "pw",
        }},
    )
    logger_module = types.ModuleType("utils.logger")
    logger_module.logger = types.SimpleNamespace(
        debug=lambda *a, **k: None, info=lambda *a, **k: None,
        warning=lambda *a, **k: None, error=lambda *a, **k: None,
    )

    store_pkg = types.ModuleType("services.fraudhunter.wide_table_service.store")
    for name, module in {
        "services": services_module,
        "services.fraudhunter": fraudhunter_module,
        "services.fraudhunter.wide_table_service": wide_table_service_module,
        "utils.config": config_module,
        "utils.logger": logger_module,
        "services.fraudhunter.wide_table_service.store": store_pkg,
    }.items():
        monkeypatch.setitem(sys.modules, name, module)

    pkg_root = _backend_root / "services" / "fraudhunter" / "wide_table_service" / "store"

    def _exec(rel, mod_name):
        spec = importlib.util.spec_from_file_location(mod_name, pkg_root / rel)
        module = importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules, mod_name, module)
        spec.loader.exec_module(module)
        return module

    return _exec("query_router.py", "services.fraudhunter.wide_table_service.store.query_router")


class TestSqlDialect:
    def _load(self, monkeypatch):
        # sql_dialect 仅依赖 utils.logger（惰性），直接 exec
        spec = importlib.util.spec_from_file_location(
            "sql_dialect_for_test",
            _backend_root / "services" / "fraudhunter" / "model_service" / "sql_dialect.py",
        )
        module = importlib.util.module_from_spec(spec)
        logger_module = types.ModuleType("utils.logger")
        logger_module.logger = types.SimpleNamespace(
            debug=lambda *a, **k: None, info=lambda *a, **k: None,
            warning=lambda *a, **k: None, error=lambda *a, **k: None,
        )
        monkeypatch.setitem(sys.modules, "utils.logger", logger_module)
        spec.loader.exec_module(module)
        return module

    def test_pg_regex(self, monkeypatch):
        m = self._load(monkeypatch)
        d = m.get_dialect('postgresql')
        assert d.regex_match("col", "abc") == "col ~* 'abc'"
        assert d.regex_match("col", "abc", negate=True) == "not col ~* 'abc'"

    def test_duckdb_regex(self, monkeypatch):
        m = self._load(monkeypatch)
        d = m.get_dialect('duckdb')
        assert d.regex_match("col", "abc") == "regexp_matches(col, 'abc', 'i')"
        assert d.regex_match("col", "abc", negate=True) == "NOT regexp_matches(col, 'abc', 'i')"

    def test_cast_and_quote_shared(self, monkeypatch):
        m = self._load(monkeypatch)
        for name in ('postgresql', 'duckdb'):
            d = m.get_dialect(name)
            assert d.cast_double("x") == "x::DOUBLE PRECISION"
            assert "NULLIF(x, '')" in d.cast_date("x")
            assert d.quote_ident("a b") == '"a b"'

    def test_unknown_falls_back_to_pg(self, monkeypatch):
        m = self._load(monkeypatch)
        assert m.get_dialect('mysql').name == 'postgresql'

    def test_regex_sql_both_dialects_execute_on_duckdb(self, monkeypatch):
        """duckdb 方言的正则表达式可直接在本地 DuckDB 执行（PG 方言的 ~* 不行）"""
        import duckdb
        m = self._load(monkeypatch)
        conn = duckdb.connect()
        duck_expr = m.get_dialect('duckdb').regex_match("'ABC123'", "abc\\d+")
        assert conn.execute(f"SELECT {duck_expr}").fetchone()[0] is True
        pg_expr = m.get_dialect('postgresql').regex_match("'x'", "x")
        with pytest.raises(Exception):
            conn.execute(f"SELECT {pg_expr}").fetchone()


class TestTableRefs:
    def test_postgresql_snapshot_keeps_pg_name(self, monkeypatch):
        qr = _load_query_router(monkeypatch)
        snap = _make_fake_snapshot('postgresql')
        ref = qr.offline_table_ref(snap, ETL)
        # 沿用回测/实时任务现有公式：{宽表}_{完整version_hash}_{yyyymmdd}
        assert ref == f"cust_wide_table_{snap.version_hash}_20260819"
        assert '~' not in ref and 'read_parquet' not in ref

    def test_duckdb_snapshot_reads_parquet_glob(self, monkeypatch):
        qr = _load_query_router(monkeypatch)
        snap = _make_fake_snapshot('duckdb', parquet_path='/data/wide_tables/cust_wide_table_abcd1234')
        ref = qr.offline_table_ref(snap, ETL)
        assert ref == (
            "read_parquet('/data/wide_tables/cust_wide_table_abcd1234/"
            "etl_date=2026-08-19/*.parquet', hive_partitioning=false)"
        )

    def test_pg_snapshot_in_duckdb_mode_uses_attach_alias(self, monkeypatch):
        qr = _load_query_router(monkeypatch)
        snap = _make_fake_snapshot('postgresql')
        ref = qr.offline_table_ref(snap, ETL, duckdb_mode=True)
        assert ref.startswith("pg_rt.public.cust_wide_table_")

    def test_realtime_table_ref(self, monkeypatch):
        qr = _load_query_router(monkeypatch)
        assert qr.realtime_table_ref("t_realtime", duckdb_mode=False) == "t_realtime"
        assert qr.realtime_table_ref("t_realtime", duckdb_mode=True) == "pg_rt.public.t_realtime"
        assert qr.realtime_table_ref(None) is None

    def test_requires_duckdb(self, monkeypatch):
        qr = _load_query_router(monkeypatch)
        assert qr.requires_duckdb(_make_fake_snapshot('duckdb')) is True
        assert qr.requires_duckdb(_make_fake_snapshot('postgresql')) is False
        assert qr.requires_duckdb(_make_fake_snapshot('postgresql'), _make_fake_snapshot('duckdb')) is True
        assert qr.requires_duckdb(None) is False

    def test_snapshot_backend_defaults_to_pg(self, monkeypatch):
        qr = _load_query_router(monkeypatch)
        assert qr.snapshot_backend(types.SimpleNamespace()) == 'postgresql'


class TestDuckQuerySessionLocal:
    """attach_pg=False 的纯本地 Parquet 查询（不依赖 PG）"""

    def test_query_local_parquet(self, monkeypatch, tmp_path):
        qr = _load_query_router(monkeypatch)
        import duckdb

        parquet_dir = tmp_path / "cust_wide_table_abcd1234" / "etl_date=2026-08-19"
        parquet_dir.mkdir(parents=True)
        conn = duckdb.connect()
        conn.execute(f"""
            COPY (SELECT 'A001' AS target_id, DATE '2026-08-19' AS etl_date, 100 AS i_amt)
            TO '{(parquet_dir / 'part-00000.parquet').as_posix()}' (FORMAT PARQUET)
        """)
        conn.close()

        ref = qr.offline_table_ref(
            _make_fake_snapshot('duckdb', parquet_path=str(tmp_path / "cust_wide_table_abcd1234")),
            ETL,
        )
        with qr.DuckQuerySession(attach_pg=False) as sess:
            df = sess.execute_df(f"SELECT count(*) AS count FROM {ref}")
            assert int(df.iloc[0]['count']) == 1
            df2 = sess.execute_df(
                f"SELECT COALESCE(i_amt::DOUBLE PRECISION, 0) AS v FROM {ref}"
            )
            assert float(df2.iloc[0]['v']) == 100.0
