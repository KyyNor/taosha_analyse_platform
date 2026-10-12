"""实时预警试跑检查集（docs/fraudhunter_offline_dual_store_plan.md 第七章阶段 12）

独立子进程运行（真实 import 链 + SQLite 元数据库 + FakePG），结果以 JSON 输出，
由 test_realtime_dry_run.py 逐项断言。用法：python checks.py --out <结果.json>
"""

import argparse
import contextlib
import io
import json
import os
import sys
import traceback
from datetime import date, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
TESTS_MODULES = HERE.parent
BACKEND = TESTS_MODULES.parents[2] / "backend"
GOLDEN = TESTS_MODULES / "pg_golden"

os.environ["TAOSHA_CONFIG_FILE"] = str(GOLDEN / "config.golden.yaml")
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(GOLDEN))
os.chdir(BACKEND)

import services  # noqa: E402,F401
import harness as h  # noqa: E402
import pandas as pd  # noqa: E402
from utils.config import settings  # noqa: E402

RT_DEP = "dep_acct_wide_table_realtime_1a2b3c4d_202610101430"
RT_CUST = "cust_wide_table_realtime_9c0d1e2f_202610101430"


def _setup(duck_snapshots=False, pg_snapshots=True, realtime=True):
    """与 golden realtime 场景相同的种子（模型/指标/版本/快照），另加实时快照记录"""
    from models.db_base import get_db_session
    from models.fraudhunter.wide_table import FraudHunterWideTableSnapshot

    engine = h.install_sqlite()
    pg = h.FakePG()
    h.install_fake_pg(pg)
    h.install_fake_spark(pg)
    with get_db_session() as db:
        h.seed_common(db)
        h.seed_models(db)
        h.seed_version(db, "dep_acct_wide_table", h.VH_DEP_OLD, h.dep_metadata(), "current", datetime(2026, 9, 1))
        h.seed_version(db, "cust_wide_table", h.VH_CUST, h.cust_metadata(), "current", datetime(2026, 9, 1))
        if pg_snapshots:
            h.seed_snapshot(db, "dep_acct_wide_table", h.VH_DEP_OLD, date(2026, 10, 8), f"dep_acct_wide_table_{h.VH_DEP_OLD}")
            h.seed_snapshot(db, "dep_acct_wide_table", h.VH_DEP_OLD, date(2026, 10, 9), f"dep_acct_wide_table_{h.VH_DEP_OLD}")
            h.seed_snapshot(db, "cust_wide_table", h.VH_CUST, date(2026, 10, 9), f"cust_wide_table_{h.VH_CUST}")
        if duck_snapshots:
            for wt, vh in (("dep_acct_wide_table", h.VH_DEP_OLD), ("cust_wide_table", h.VH_CUST)):
                db.add(FraudHunterWideTableSnapshot(
                    wide_table_name=wt, version_hash=vh, etl_date=date(2026, 10, 9),
                    parquet_file_path=f"/srv/parquet/{wt}_{vh}", row_count=3, column_count=5,
                    status="ready", storage_backend="duckdb", generation_time=datetime(2026, 10, 10, 7, 0),
                ))
        if realtime:
            for wt, table in (("dep_acct_wide_table_realtime", RT_DEP), ("cust_wide_table_realtime", RT_CUST)):
                db.add(FraudHunterWideTableSnapshot(
                    wide_table_name=wt, version_hash=None, etl_date=date(2026, 10, 10),
                    parquet_file_path=table, row_count=3, column_count=4, status="ready",
                    generation_time=datetime(2026, 10, 10, 14, 44),
                ))
        db.flush()
    return engine, pg


def _pg_df(sql=None):
    return pd.DataFrame({
        "目标ID": ["A001", "A002", "A003"],
        "近30天交易额": [12000.5, 300.0, 5.0],
        "model_hit_array": [[101], [101, 102], [102]],
    })


def _duck_df():
    return pd.DataFrame({
        "目标ID": ["A001", "A002", "A004"],
        "近30天交易额": [12000.5 + 1e-12, 301.0, 7.0],
        "model_hit_array": [[101], [101, 102], [102]],
    })


class FakeDuckSession:
    executed = []

    def __init__(self, df):
        self.df = df

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute_df(self, sql):
        FakeDuckSession.executed.append(sql)
        return self.df


def _install_duck(df):
    from services.fraudhunter.wide_table_service.store import query_router
    FakeDuckSession.executed = []
    query_router.get_query_session = lambda attach_pg=True: FakeDuckSession(df)


def _run(backend, **kwargs):
    from models.db_base import SessionLocal
    from services.fraudhunter.model_service.realtime_dry_run import run_realtime_match_dry_run
    db = SessionLocal()
    try:
        return run_realtime_match_dry_run(db, backend, **kwargs)
    finally:
        db.rollback()
        db.close()


def _write_events(pg):
    return [e for e in pg.events if not (e[0] == "execute_sql" and e[3] is True)]


def _count(engine, table):
    from sqlalchemy import text
    with engine.connect() as conn:
        return conn.execute(text(f"SELECT count(*) FROM {table}")).scalar()


# =============================================================================

def check_pg_dry_run_sql_identical_to_production(tmp):
    """PG 试跑生成的模型匹配 SQL 与线上 step2（golden 基准）逐字一致"""
    engine, pg = _setup()
    pg.fetch_handlers.append((lambda s: True, _pg_df))
    report = _run("postgresql", show_sql=True, realtime_tables={})
    res = report["backends"]["postgresql"]
    assert res["error"] is None, res
    golden = json.loads((GOLDEN / "golden" / "realtime.json").read_text(encoding="utf-8"))
    prod_sql = next(e[1] for e in golden["events"] if e[0] == "execute_sql" and "实时模型匹配SQL" in e[1])
    assert h.normalize_sql(res["sql"]) == prod_sql, "试跑 SQL 与线上 step2 不一致"
    executed = [e[1] for e in pg.events if e[0] == "execute_sql"]
    assert executed == [prod_sql], executed
    assert res["engine"] == "postgresql" and res["hit_count"] == 4, res
    assert res["per_model"] == {"M001": 2, "M002": 2}, res["per_model"]
    assert report["realtime_tables"] == {"dep_acct_no": RT_DEP, "cust_no": RT_CUST}, report["realtime_tables"]


def check_dry_run_writes_nothing(tmp):
    """不写执行记录/命中/告警/管控，不产生任何 PG 写操作"""
    from services.fraudhunter.model_service import model_hit_alert_manager as mham
    engine, pg = _setup(duck_snapshots=True)
    pg.fetch_handlers.append((lambda s: True, _pg_df))
    _install_duck(_duck_df())

    def forbidden(*a, **k):
        raise AssertionError("试跑不应调用告警管理器")
    mham.ModelHitAlertManager.__init__ = forbidden
    before = {t: _count(engine, t) for t in (
        "fraudhunter_model_execution", "fraudhunter_model_hit_record",
        "fraudhunter_model_alert_control_record", "fraudhunter_wide_table_snapshot")}
    _run("both")
    after = {t: _count(engine, t) for t in before}
    assert before == after, (before, after)
    assert _write_events(pg) == [], _write_events(pg)


def check_duckdb_backend_routes_to_duck_session(tmp):
    engine, pg = _setup(duck_snapshots=True)
    _install_duck(_duck_df())
    report = _run("duckdb", show_sql=True)
    res = report["backends"]["duckdb"]
    assert res["error"] is None and res["engine"] == "duckdb", res
    sql = res["sql"]
    assert "read_parquet('/srv/parquet/dep_acct_wide_table_1a2b3c4d/etl_date=2026-10-09/*.parquet'" in sql, sql
    assert f"pg_rt.public.{RT_DEP}" in sql and f"pg_rt.public.{RT_CUST}" in sql, sql
    assert "regexp_matches" in sql, "DuckDB 方言未生效"
    assert FakeDuckSession.executed == [sql]
    assert not any(e[0] == "execute_sql" for e in pg.events), "duckdb 试跑不应在 PG 执行"
    assert res["snapshots"]["dep_acct_no"]["storage_backend"] == "duckdb"


def check_both_diff(tmp):
    engine, pg = _setup(duck_snapshots=True)
    pg.fetch_handlers.append((lambda s: True, _pg_df))
    _install_duck(_duck_df())
    report = _run("both")
    diff = report["diff"]
    assert diff["identical"] is False
    assert diff["only_postgresql"] == [{"target_id": "A003", "model_code": "M002"}], diff
    assert diff["only_duckdb"] == [{"target_id": "A004", "model_code": "M002"}], diff
    mism = {(m["target_id"], m["model_code"], m["column"]) for m in diff["value_mismatches"]}
    # A001 差 1e-12 在容差内；A002 差 1.0 超容差（两个模型各记一次）
    assert mism == {("A002", "M001", "近30天交易额"), ("A002", "M002", "近30天交易额")}, mism
    assert report["warnings"] == [], report["warnings"]


def check_both_identical(tmp):
    engine, pg = _setup(duck_snapshots=True)
    pg.fetch_handlers.append((lambda s: True, _pg_df))
    _install_duck(_pg_df())
    assert _run("both")["diff"]["identical"] is True


def check_forced_backend_no_fallback(tmp):
    """强制 duckdb 但无 duckdb 快照：报错且不执行，不回退到 PG 快照"""
    engine, pg = _setup(duck_snapshots=False)
    _install_duck(_duck_df())
    report = _run("duckdb")
    res = report["backends"]["duckdb"]
    assert res["error"] and "duckdb" in res["error"], res
    assert FakeDuckSession.executed == [] and not pg.events, pg.events
    assert report["warnings"], report


def check_snapshot_mismatch_warns(tmp):
    """both 下两侧离线快照日期不一致时告警（结果不可直接比较）"""
    from models.db_base import get_db_session
    from models.fraudhunter.wide_table import FraudHunterWideTableSnapshot
    engine, pg = _setup(duck_snapshots=False)
    with get_db_session() as db:
        db.add(FraudHunterWideTableSnapshot(
            wide_table_name="dep_acct_wide_table", version_hash=h.VH_DEP_OLD, etl_date=date(2026, 10, 8),
            parquet_file_path="/srv/parquet/x", row_count=3, column_count=5, status="ready",
            storage_backend="duckdb", generation_time=datetime(2026, 10, 9, 1, 0),
        ))
    pg.fetch_handlers.append((lambda s: True, _pg_df))
    _install_duck(_pg_df())
    report = _run("both")
    assert any("dep_acct_no 离线快照不一致" in w for w in report["warnings"]), report["warnings"]


def check_etl_date_and_model_filter(tmp):
    engine, pg = _setup()
    pg.fetch_handlers.append((lambda s: True, _pg_df))
    report = _run("postgresql", model_codes=["M002"], etl_date=date(2026, 10, 8), show_sql=True)
    res = report["backends"]["postgresql"]
    assert res["snapshots"]["dep_acct_no"]["etl_date"] == "2026-10-08", res["snapshots"]
    assert res["snapshots"]["cust_no"] is None  # 客户宽表 10-08 无快照
    assert "THEN 101" not in res["sql"] and "THEN 102" in res["sql"]
    assert res["per_model"] == {"M002": 2}, res["per_model"]


def check_invalid_inputs(tmp):
    from services.fraudhunter.model_service.realtime_dry_run import DryRunError
    engine, pg = _setup(realtime=False)
    for kwargs, msg in (
        ({"backend": "mysql"}, "backend"),
        ({"backend": "postgresql", "model_codes": ["M003"]}, "未上线"),
        ({"backend": "postgresql"}, "实时宽表分区"),
    ):
        try:
            _run(**kwargs)
            raise AssertionError(f"应失败: {kwargs}")
        except DryRunError as e:
            assert msg in str(e), (msg, str(e))
    # 显式指定实时分区即可运行
    pg.fetch_handlers.append((lambda s: True, _pg_df))
    report = _run("postgresql", realtime_tables={"dep_acct_no": RT_DEP})
    assert report["realtime_tables"]["dep_acct_no"] == RT_DEP


def check_api_route(tmp):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from api.fraudhunter import backend_compare_routes as routes
    from middleware.auth_middleware import get_current_user
    import inspect

    engine, pg = _setup(duck_snapshots=True)
    pg.fetch_handlers.append((lambda s: True, _pg_df))
    _install_duck(_duck_df())
    app = FastAPI()
    app.include_router(routes.router, prefix="/api/taosha/v1/fraudhunter")
    app.dependency_overrides[get_current_user] = lambda: type("U", (), {"user_id": "tester"})()
    client = TestClient(app)
    url = "/api/taosha/v1/fraudhunter/backend-compare/realtime-match"
    r = client.post(url, json={"backend": "both", "limit": 1})
    assert r.status_code == 200, r.text
    body = r.json()
    assert "hits" not in body
    assert body["diff"]["only_postgresql_count"] == 1 and body["diff"]["identical"] is False, body["diff"]
    assert len(body["backends"]["postgresql"]["sample"]) == 1
    r = client.post(url, json={"backend": "postgresql", "model_codes": ["NOPE"]})
    assert r.status_code == 400 and "未上线" in r.json()["detail"], r.text
    app.dependency_overrides.clear()
    r = client.post(url, json={"backend": "postgresql"})
    assert r.status_code == 401, r.text
    for route in routes.router.routes:
        assert not inspect.iscoroutinefunction(route.endpoint)


def check_cli(tmp):
    import importlib.util
    engine, pg = _setup(duck_snapshots=True)
    pg.fetch_handlers.append((lambda s: True, _pg_df))
    _install_duck(_duck_df())
    spec = importlib.util.spec_from_file_location("dry_run_cli", BACKEND / "scripts" / "realtime_alert_dry_run.py")
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    out_csv = Path(tmp) / "hits.csv"
    argv = sys.argv
    sys.argv = ["realtime_alert_dry_run.py", "--backend", "both", "--output", str(out_csv), "--limit", "2"]
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            try:
                cli.main()
                code = 0
            except SystemExit as e:
                code = e.code
    finally:
        sys.argv = argv
    text = buf.getvalue()
    assert code == 1, (code, text)  # 存在差异 → 非零退出码，便于脚本化判断
    assert "仅 PG 命中: 1" in text and "存在差异" in text, text
    df = pd.read_csv(out_csv)
    assert sorted(df["backend"].unique()) == ["duckdb", "postgresql"], df
    assert (Path(tmp) / "hits_diff.json").exists()
    assert cli._parse_realtime_tables(["dep_acct_no=t1", "cust_no=t2"]) == {"dep_acct_no": "t1", "cust_no": "t2"}


def main():
    import shutil
    import tempfile
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    results = {}
    for name, fn in [(k, v) for k, v in globals().items() if k.startswith("check_") and callable(v)]:
        tmp = tempfile.mkdtemp(prefix="dry_run_check_")
        saved_gqs = None
        try:
            from services.fraudhunter.wide_table_service.store import query_router
            saved_gqs = query_router.get_query_session
            fn(tmp)
            results[name] = "ok"
        except BaseException:  # noqa: BLE001
            results[name] = traceback.format_exc()
        finally:
            if saved_gqs is not None:
                query_router.get_query_session = saved_gqs
            shutil.rmtree(tmp, ignore_errors=True)
    Path(args.out).write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
