"""PG 零影响守护：场景执行器（docs/fraudhunter_offline_dual_store_plan.md 阶段 8）

在指定 backend 源码树上运行一组固定场景，记录 PG 侧执行的全部 SQL、写入的数据形状
以及 MySQL 元数据的最终状态，输出为 JSON。同一套场景分别在 main 与当前分支运行，
结果逐字对比，即可证明 offline_store=postgresql 时行为与 main 一致。

用法（独立子进程运行，避免污染 pytest 进程的 sys.modules）：
    python harness.py --backend-root <backend目录> --out <结果.json> [--write-config]

--write-config：目标源码树不支持 TAOSHA_CONFIG_FILE（如 main 分支）时，
把测试配置复制为 <backend>/config/config.yaml（仅用于一次性采集基准的临时 worktree）。

边界替身：
- MySQL 元数据：SQLite 内存库（真实 ORM 模型 + 真实查询语义）；
- PG：替换 AnalyzeDBConnector 的引擎/执行入口为 FakePG（记录 SQL、按内置"世界状态"应答）；
- Spark：替换 spark_utils.query_sql / PySparkService（记录 SQL、返回固定行）。
"""

import argparse
import asyncio
import json
import os
import re
import shutil
import sys
import threading
from datetime import date, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
GOLDEN_CONFIG = HERE / "config.golden.yaml"

TODAY = date(2026, 10, 10)
NOW_STR = "202610101444"
FIXED_NOW = datetime(2026, 10, 10, 14, 44, 0)

# 版本哈希（与生产一致为 sha256 前 8 位，取值固定）
VH_DEP_OLD = "1a2b3c4d"
VH_DEP_NEW = "5e6f7a8b"
VH_CUST = "9c0d1e2f"

_GEN_TIME_RE = re.compile(r"^-- 生成时间: .*$", re.M)
_EXEC_TIME_RE = re.compile(r"^执行时间: .*$", re.M)


def normalize_sql(sql) -> str:
    """规整文本：TextClause 取文本；仅抹掉 SQL 注释/回测日志中的当前时间（非确定字段）"""
    if hasattr(sql, "text"):
        sql = sql.text
    sql = _GEN_TIME_RE.sub("-- 生成时间: <NOW>", str(sql))
    return _EXEC_TIME_RE.sub("执行时间: <NOW>", sql)


def _jsonable(value):
    if isinstance(value, str):
        return normalize_sql(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if hasattr(value, "item"):  # numpy 标量
        return value.item()
    return value


# =============================================================================
# FakePG：记录 + 世界状态应答
# =============================================================================

class FakePG:
    _TABLE_EXISTS_RE = re.compile(r"tablename\s*=\s*:(\w+)", re.I)
    _COUNT_RE = re.compile(r"SELECT\s+COUNT\(\*\)\s+FROM\s+(\w+)", re.I)
    _CREATE_RE = re.compile(r"CREATE\s+(?:UNLOGGED\s+)?TABLE\s+IF\s+NOT\s+EXISTS\s+(\w+)", re.I)
    _DROP_RE = re.compile(r"DROP\s+TABLE\s+IF\s+EXISTS\s+(\w+)", re.I)

    def __init__(self):
        self.events = []
        self.tables = {}  # 表名 -> 行数
        self.fetch_handlers = []  # [(predicate(sql), DataFrame工厂)]
        self._lock = threading.Lock()

    def record(self, *event):
        with self._lock:
            self.events.append(_jsonable(list(event)))

    # ---- 世界状态应答 ----
    def answer(self, sql: str, params: dict):
        """返回 (scalar, rows, rowcount)"""
        params = params or {}
        m = self._TABLE_EXISTS_RE.search(sql)
        if m and "pg_tables" in sql:
            name = params.get(m.group(1))
            return (name in self.tables), [(name in self.tables,)], 1
        m = self._COUNT_RE.search(sql)
        if m:
            n = self.tables.get(m.group(1), 0)
            return n, [(n,)], 1
        m = self._CREATE_RE.search(sql)
        if m:
            self.tables.setdefault(m.group(1), 0)
            return None, [], 0
        m = self._DROP_RE.search(sql)
        if m:
            self.tables.pop(m.group(1), None)
            return None, [], 0
        if sql.lstrip().upper().startswith("INSERT"):
            return None, [], 1000
        return None, [], 0

    def fetch_df(self, sql: str, params: dict):
        import pandas as pd

        m = self._TABLE_EXISTS_RE.search(sql)
        if m and "pg_tables" in sql:
            name = (params or {}).get(m.group(1))
            return pd.DataFrame({"exists": [name in self.tables]})
        for predicate, factory in self.fetch_handlers:
            if predicate(sql):
                return factory(sql)
        return pd.DataFrame()


class _FakeResult:
    def __init__(self, scalar, rows, rowcount):
        self._scalar, self._rows, self.rowcount = scalar, rows, rowcount

    def scalar(self):
        return self._scalar

    def fetchall(self):
        return list(self._rows)

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def __iter__(self):
        return iter(self._rows)


class _FakeConn:
    def __init__(self, pg: FakePG):
        self.pg = pg

    def execute(self, clause, params=None):
        sql = normalize_sql(clause)
        self.pg.record("engine.execute", sql, params or {})
        return _FakeResult(*self.pg.answer(sql, params))

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _FakeEngine:
    def __init__(self, pg: FakePG):
        self.pg = pg

    def connect(self):
        return _FakeConn(self.pg)

    def begin(self):
        return _FakeConn(self.pg)

    def raw_connection(self):
        raise AssertionError("harness: raw_connection 不应被调用（batch_insert_copy 已替身）")


def install_fake_pg(pg: FakePG):
    from utils.analyze_db_utils import AnalyzeDBConnector

    AnalyzeDBConnector._engine = None
    AnalyzeDBConnector.get_engine = classmethod(lambda cls: _FakeEngine(pg))

    def execute_sql(cls, sql, params=None, fetch_df=False):
        sql = normalize_sql(sql)
        pg.record("execute_sql", sql, params or {}, bool(fetch_df))
        if fetch_df:
            return pg.fetch_df(sql, params)
        pg.answer(sql, params)
        return None

    def batch_insert(cls, table_name, df, chunksize=1000, if_exists="append"):
        pg.record("batch_insert", table_name, list(df.columns), len(df), if_exists)
        pg.tables[table_name] = pg.tables.get(table_name, 0) + len(df)
        return len(df)

    def batch_insert_copy(cls, table_name, df, *args, **kwargs):
        pg.record("batch_insert_copy", table_name, list(df.columns), len(df),
                  _jsonable(df.astype(str).to_dict("records")))
        return len(df)

    def truncate_table(table_name):
        pg.record("truncate_table", table_name)

    AnalyzeDBConnector.execute_sql = classmethod(execute_sql)
    AnalyzeDBConnector.batch_insert = classmethod(batch_insert)
    AnalyzeDBConnector.batch_insert_copy = classmethod(batch_insert_copy)
    AnalyzeDBConnector.truncate_table = staticmethod(truncate_table)


# =============================================================================
# Spark 替身
# =============================================================================

def _spark_rows_for(sql: str):
    """按 PIVOT SQL 中出现的指标列生成 3 行固定数据"""
    codes = sorted(set(re.findall(r"'(i_\w+)' AS (i_\w+)", sql)))
    rows = []
    for i in range(3):
        row = {"target_id": f"T{i:03d}"}
        for code, _ in codes:
            row[code] = str(i * 10 + len(code) % 7)
        rows.append(row)
    return rows


def install_fake_spark(pg: FakePG):
    from utils import spark_utils as su

    def query_sql(sql, return_type="dict", *args, **kwargs):
        pg.record("spark.query_sql", normalize_sql(sql), return_type)
        if return_type is None:
            return None
        return _spark_rows_for(sql)

    su.spark_utils.query_sql = query_sql

    class _FakeDF:
        def __init__(self, sql):
            self._rows = _spark_rows_for(sql)
            self.columns = list(self._rows[0].keys()) + ["etl_date"]

        def count(self):
            return len(self._rows)

        @property
        def write(self):
            return _FakeWriter()

    class _FakeWriter:
        def mode(self, m):
            self._mode = m
            return self

        def option(self, k, v):
            return self

        def jdbc(self, url, table, properties=None):
            pg.record("pyspark.jdbc_write", table, self._mode)
            pg.tables[table] = pg.tables.get(table, 0) + 3

    class _FakeSpark:
        def sql(self, sql):
            pg.record("pyspark.sql", normalize_sql(sql))
            return _FakeDF(sql)

    class FakePySparkService:
        def __init__(self, *a, **k):
            self.spark = _FakeSpark()

        def is_initialized(self):
            return True

        def initialize(self):
            pass

        def shutdown(self):
            pg.record("pyspark.shutdown")

    su.PySparkService = FakePySparkService


# =============================================================================
# MySQL（SQLite 内存库）
# =============================================================================

def install_sqlite():
    from sqlalchemy import BigInteger, create_engine
    from sqlalchemy.ext.compiler import compiles
    from sqlalchemy.pool import StaticPool

    @compiles(BigInteger, "sqlite")
    def _bigint_as_integer(type_, compiler, **kw):  # SQLite 仅 INTEGER 主键自增
        return "INTEGER"

    import models.db_base as db_base
    import models.fraudhunter.wide_table  # noqa: F401
    import models.fraudhunter.indicator  # noqa: F401
    import models.fraudhunter.risk_control_model  # noqa: F401
    import models.fraudhunter.dry_run_task  # noqa: F401
    import models.fraudhunter.model_execution_tracking  # noqa: F401

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    db_base.Base.metadata.create_all(engine)
    db_base.SessionLocal.configure(bind=engine)
    return engine


def dump_tables(engine, specs):
    """导出指定表的最终状态（剔除自增 id / 时间戳等非确定列）"""
    from sqlalchemy import inspect, text

    skip = {"id", "created_at", "updated_at", "generation_time", "execution_start_time",
            "execution_end_time", "start_time", "end_time", "target_at", "current_at",
            "history_at", "skipped_at", "finish_time", "duration_seconds",
            # 分支新增列：main 不存在，单独断言其取值（见 test_pg_golden）
            "storage_backend"}
    out = {}
    insp = inspect(engine)
    with engine.connect() as conn:
        for table, order_by in specs:
            cols = [c["name"] for c in insp.get_columns(table) if c["name"] not in skip]
            rows = conn.execute(text(
                f"SELECT {', '.join(cols)} FROM {table} ORDER BY {order_by}"
            )).mappings().all()
            out[table] = [
                {k: (normalize_sql(v) if isinstance(v, str) else _jsonable(v)) for k, v in r.items()}
                for r in rows
            ]
    return out


# =============================================================================
# 种子数据
# =============================================================================

def _meta(ind_id, code, data_type, task_id, version=1, name=None):
    return str(ind_id), {
        "indicator_code": code,
        "indicator_name": name or code,
        "data_type": data_type,
        "indicator_task_id": task_id,
        "version": version,
    }


DEP_INDICATORS = [
    # (id, code, data_type, type, task_id, name)
    (1, "i_dep_acct_no_offline_00001", "string", "offline", 1, "客户号"),
    (2, "i_dep_acct_no_offline_00002", "string", "offline", 1, "机构号"),
    (3, "i_dep_acct_no_offline_00007", "string", "offline", 1, "客户类型"),
    (4, "i_dep_acct_no_offline_00010", "numeric", "offline", 1, "近30天交易额"),
    (5, "i_dep_acct_no_offline_00011", "date", "offline", 1, "开户日期"),
    (6, "i_dep_acct_no_offline_00012", "string", "offline", 1, "渠道"),
    (7, "i_dep_acct_no_realtime_00001", "numeric", "realtime", 2, "当日转出笔数"),
]
CUST_INDICATORS = [
    (11, "i_cust_no_offline_00001", "numeric", "offline", 3, "客户年龄"),
    (12, "i_cust_no_realtime_00001", "numeric", "realtime", 4, "当日登录次数"),
]


def seed_common(db):
    from models.fraudhunter.indicator import (
        FraudHunterIndicatorDefinition, FraudHunterIndicatorTask,
    )
    from models.fraudhunter.model_execution_tracking import FraudHunterSystemConfig

    tasks = [
        (1, "TASK_DEP_OFF", "dep_acct_no", None),
        (2, "TASK_DEP_RT", "dep_acct_no",
         "SELECT target_id, cnt AS i_dep_acct_no_realtime_00001, etl_date FROM realtime_oss_inct_new r "
         "JOIN offline_dep_acct_no_table o ON r.acct = o.target_id "
         "WHERE r.tran_date = '${date}' AND r.chnl IN (${chnl_list}) AND o.i_dep_acct_no_offline_00002 = '${branch}'"),
        (3, "TASK_CUST_OFF", "cust_no", None),
        (4, "TASK_CUST_RT", "cust_no",
         "SELECT target_id, n AS i_cust_no_realtime_00001 FROM realtime_oss_inct_new r "
         "JOIN offline_cust_no_table c ON r.cust = c.target_id WHERE r.tran_date = '${date}'"),
    ]
    for tid, code, ot, rt_sql in tasks:
        db.add(FraudHunterIndicatorTask(
            id=tid, task_code=code, task_name=code, logic_content="SELECT 1",
            realtime_logic_content=rt_sql, object_type=ot, status="online",
        ))
    for ind_id, code, dt, itype, task_id, name in DEP_INDICATORS + CUST_INDICATORS:
        db.add(FraudHunterIndicatorDefinition(
            id=ind_id, indicator_code=code, indicator_name=name, indicator_type=itype,
            object_type="dep_acct_no" if "dep_acct" in code else "cust_no",
            data_type=dt, indicator_task_id=task_id, status="online",
        ))
    db.add(FraudHunterSystemConfig(
        id=1, config_category="sql_variable", config_key="chnl_list", config_desc="渠道",
        config_type="list", config_value={"value": ["APP", "WEB"]}, sql_in_convert=1,
    ))
    db.add(FraudHunterSystemConfig(
        id=2, config_category="sql_variable", config_key="branch", config_desc="机构",
        config_type="string", config_value={"value": "0101"}, sql_in_convert=0,
    ))
    db.flush()


def dep_metadata(include_realtime=True, codes=None):
    md = {}
    for ind_id, code, dt, itype, task_id, name in DEP_INDICATORS:
        if itype == "realtime" and not include_realtime:
            continue
        if codes is not None and code not in codes:
            continue
        k, v = _meta(ind_id, code, dt, task_id, name=name)
        md[k] = v
    return md


def cust_metadata():
    return dict(_meta(i, c, dt, t, name=n) for i, c, dt, _it, t, n in CUST_INDICATORS)


def seed_version(db, wide_table, vh, metadata, status, created_at):
    from models.fraudhunter.wide_table import FraudHunterWideTableVersion

    v = FraudHunterWideTableVersion(
        wide_table_name=wide_table, version_hash=vh, indicator_metadata=metadata,
        status=status, created_at=created_at,
    )
    db.add(v)
    db.flush()
    return v


def seed_snapshot(db, wide_table, vh, etl_date, path, rows=3, gen=None):
    from models.fraudhunter.wide_table import FraudHunterWideTableSnapshot

    s = FraudHunterWideTableSnapshot(
        wide_table_name=wide_table, version_hash=vh, etl_date=etl_date,
        parquet_file_path=path, row_count=rows, column_count=5, status="ready",
        generation_time=gen or FIXED_NOW,
    )
    db.add(s)
    db.flush()
    return s


RULE_M1 = {
    "logic": "AND",
    "rules": [
        {"type": "condition", "indicator": "i_dep_acct_no_realtime_00001", "operator": ">",
         "value": {"type": "constant", "value": 5}},
        {"type": "condition", "indicator": "i_dep_acct_no_offline_00010", "operator": ">=",
         "value": {"type": "constant", "value": 10000}},
    ],
}
RULE_M1_HISTORY = {
    "logic": "AND",
    "rules": [
        {"type": "condition", "indicator": "i_dep_acct_no_realtime_00001", "operator": ">",
         "value": {"type": "constant", "value": 8}},
        {"type": "condition", "indicator": "i_cust_no_realtime_00001", "operator": ">",
         "value": {"type": "constant", "value": 3}},
    ],
}
RULE_M2 = {
    "logic": "OR",
    "rules": [
        {"type": "condition", "indicator": "i_dep_acct_no_offline_00012", "operator": "regexp",
         "value": {"type": "constant", "value": "app\\d+"}},
        {"type": "group", "logic": "AND", "rules": [
            {"type": "condition", "indicator": "i_dep_acct_no_offline_00011", "operator": "<",
             "value": {"type": "constant", "value": "2020-01-01"}},
            {"type": "condition", "indicator": "i_cust_no_offline_00001", "operator": ">=",
             "value": {"type": "constant", "value": 60}},
            {"type": "condition", "indicator": "i_dep_acct_no_offline_00010", "operator": ">",
             "value": {"type": "indicator", "indicator": "i_dep_acct_no_realtime_00001"}},
        ]},
    ],
}


def seed_models(db):
    from models.fraudhunter.risk_control_model import (
        FraudHunterModelDefinition, FraudHunterModelHistory,
    )

    m1 = FraudHunterModelDefinition(
        id=101, model_code="M001", model_name="大额转出", model_type="normal",
        rule_config=RULE_M1, current_version=2, status="online",
    )
    m2 = FraudHunterModelDefinition(
        id=102, model_code="M002", model_name="老户异常", model_type="normal",
        rule_config=RULE_M2, current_version=1, status="online",
    )
    m3 = FraudHunterModelDefinition(
        id=103, model_code="M003", model_name="草稿", model_type="normal",
        rule_config=RULE_M1, current_version=1, status="draft",
    )
    db.add_all([m1, m2, m3])
    db.flush()
    db.add(FraudHunterModelHistory(
        model_id=101, version=2, model_code="M001", model_name="大额转出",
        rule_config=RULE_M1_HISTORY, change_type="publish",
    ))
    db.flush()


# =============================================================================
# 场景
# =============================================================================

def _matched_df_factory(sql):
    import pandas as pd

    return pd.DataFrame({
        "账号": ["A001", "A002"], "目标ID": ["A001", "A002"],
        "近30天交易额": [12000.5, float("nan")], "model_hit_array": [[101], [101, 102]],
    })


def _realtime_task_df_factory(sql):
    import pandas as pd

    if "i_dep_acct_no_realtime_00001" in sql:
        return pd.DataFrame({
            "target_id": ["A001", "A002", "A003"],
            "i_dep_acct_no_realtime_00001": ["7", "", "x"],
            "etl_date": ["2026-10-10"] * 3,
        })
    return pd.DataFrame({"target_id": ["C001"], "i_cust_no_realtime_00001": ["4"]})


def scenario_realtime(ctx):
    """实时任务：step1 实时指标加工 + step2 在线模型匹配"""
    from models.db_base import get_db_session
    from services.scheduler.jobs import realtime_indicator_job as rij

    pg = ctx["pg"]
    with get_db_session() as db:
        seed_common(db)
        seed_models(db)
        seed_version(db, "dep_acct_wide_table", VH_DEP_OLD, dep_metadata(), "current", datetime(2026, 9, 1))
        seed_version(db, "cust_wide_table", VH_CUST, cust_metadata(), "current", datetime(2026, 9, 1))
        seed_snapshot(db, "dep_acct_wide_table", VH_DEP_OLD, date(2026, 10, 8), f"dep_acct_wide_table_{VH_DEP_OLD[:8]}")
        seed_snapshot(db, "dep_acct_wide_table", VH_DEP_OLD, date(2026, 10, 9), f"dep_acct_wide_table_{VH_DEP_OLD[:8]}")
        seed_snapshot(db, "cust_wide_table", VH_CUST, date(2026, 10, 9), f"cust_wide_table_{VH_CUST[:8]}")
    # cust 实时表已存在、dep 实时表不存在（覆盖建表分支）
    pg.tables[f"cust_wide_table_realtime_{VH_CUST[:8]}"] = 0
    pg.fetch_handlers.append((lambda s: "realtime_oss_inct_new" in s, _realtime_task_df_factory))
    pg.fetch_handlers.append((lambda s: "实时模型匹配SQL" in s, lambda s: __import__("pandas").DataFrame()))

    today_str = TODAY.strftime("%Y-%m-%d")
    with get_db_session() as db:
        out = rij.step1_generate_realtime_indicators(db, TODAY, today_str, NOW_STR)
    if len(out) == 3:
        offline_tables, duckdb_mode, generated = out
        assert duckdb_mode is False, "PG 模式下实时任务不应进入 duckdb_mode"
    else:
        offline_tables, generated = out
    ctx["extra"]["offline_tables"] = offline_tables
    ctx["extra"]["generated_realtime_tables"] = generated

    with get_db_session() as db:
        if len(out) == 3:
            result = rij.step2_online_model_executor(db, offline_tables, generated, duckdb_mode=duckdb_mode)
        else:
            result = rij.step2_online_model_executor(db, offline_tables, generated)
    ctx["extra"]["step2_result"] = [r is None for r in result]
    return [
        ("fraudhunter_wide_table_snapshot", "wide_table_name, etl_date"),
        ("fraudhunter_model_execution", "id"),
    ]


def scenario_backtest(ctx):
    """模型历史回测：按日选快照 → 生成回测 SQL → 执行 → 结果处理"""
    from models.db_base import get_db_session
    from models.fraudhunter.dry_run_task import FraudHunterDryRunExecution
    from services.fraudhunter.model_service.model_executor import ModelExecutor

    pg = ctx["pg"]
    pg.fetch_handlers.append((lambda s: True, _matched_df_factory))

    async def _no_sleep(*_a, **_k):
        return None

    asyncio.sleep = _no_sleep
    with get_db_session() as db:
        seed_common(db)
        seed_models(db)
        seed_version(db, "dep_acct_wide_table", VH_DEP_OLD, dep_metadata(), "history", datetime(2026, 9, 1))
        seed_version(db, "dep_acct_wide_table", VH_DEP_NEW, dep_metadata(), "current", datetime(2026, 10, 1))
        seed_version(db, "cust_wide_table", VH_CUST, cust_metadata(), "current", datetime(2026, 9, 1))
        for d in (date(2026, 10, 7), date(2026, 10, 8), date(2026, 10, 9)):
            seed_snapshot(db, "dep_acct_wide_table", VH_DEP_OLD, d, f"dep_acct_wide_table_{VH_DEP_OLD[:8]}")
            seed_snapshot(db, "cust_wide_table", VH_CUST, d, f"cust_wide_table_{VH_CUST[:8]}")
        # 10-09 存在新版本快照（应优先选新版本）
        seed_snapshot(db, "dep_acct_wide_table", VH_DEP_NEW, date(2026, 10, 9), f"dep_acct_wide_table_{VH_DEP_NEW[:8]}")
        for model_id, exec_id in ((101, "EXEC-M1"), (102, "EXEC-M2")):
            db.add(FraudHunterDryRunExecution(
                task_type="model", task_id=model_id, execution_id=exec_id, status="running",
            ))
        db.flush()

    executor = ModelExecutor()
    for model_id, exec_id in ((101, "EXEC-M1"), (102, "EXEC-M2")):
        with get_db_session() as db:
            result = asyncio.run(executor.execute_backtest(
                db, exec_id, model_id, "2026-10-08", "2026-10-10",
            ))
        ctx["extra"][f"backtest_{exec_id}"] = {
            k: result.get(k) for k in (
                "total_days", "success_days", "skipped_days", "failed_days",
                "generated_sqls", "matched_records", "version_fallbacks", "warnings",
                "total_rows_matched",
            )
        }
    return [("fraudhunter_dryrun_execution", "execution_id")]


def scenario_indicator_query(ctx):
    """指标查询：按快照查询宽表数据（count + 分页）"""
    import pandas as pd
    from models.db_base import get_db_session
    from services.fraudhunter.indicator_service.indicator_query_service import IndicatorQueryService

    pg = ctx["pg"]

    def _factory(sql):
        if "count" in sql.lower().split("from")[0]:
            return pd.DataFrame({"count": [2]})
        return pd.DataFrame({"目标ID": ["A001", "A002"], "近30天交易额": [1.5, 2.0]})

    pg.fetch_handlers.append((lambda s: True, _factory))
    with get_db_session() as db:
        seed_common(db)
        seed_version(db, "dep_acct_wide_table", VH_DEP_OLD, dep_metadata(), "current", datetime(2026, 9, 1))
        snap = seed_snapshot(db, "dep_acct_wide_table", VH_DEP_OLD, date(2026, 10, 9),
                             f"dep_acct_wide_table_{VH_DEP_OLD[:8]}")
        snap_id = snap.id

    requests = [
        {"snapshot_id": snap_id, "page": 1, "page_size": 50},
        {"snapshot_id": snap_id, "page": 2, "page_size": 20, "target_id": "A0'01",
         "conditions": [
             {"field": "i_dep_acct_no_offline_00010", "operator": ">=", "value": "100"},
             {"field": "i_dep_acct_no_offline_00012", "operator": "like", "value": "app"},
             {"field": "i_dep_acct_no_offline_00011", "operator": "<", "value": "2020-01-01"},
             {"field": "i_dep_acct_no_offline_00002", "operator": "=", "value": "0101"},
         ]},
    ]
    results = []
    for req in requests:
        with get_db_session() as db:
            res = IndicatorQueryService(db).query_data(req)
        res.pop("storage_backend", None)
        results.append(res)
    ctx["extra"]["query_results"] = results
    return []


def _seed_progress(db, metadata, etl_dates):
    from models.fraudhunter.wide_table import FraudHunterIndicatorRunProgress

    pairs = {(m["indicator_task_id"], m["version"]) for m in metadata.values()}
    for d in etl_dates:
        for task_id, ver in sorted(pairs):
            db.add(FraudHunterIndicatorRunProgress(
                indicator_task_id=task_id, indicator_version=ver, etl_date=d, finish_time=FIXED_NOW,
            ))
    db.flush()


SYNC_DATES = [date(2026, 10, 9), date(2026, 10, 8), date(2026, 10, 7)]


def _run_sync(ctx, wide_table="dep_acct_wide_table"):
    from services.fraudhunter.wide_table_service.sync_service import WideTableSyncService

    WideTableSyncService._calculate_etl_dates = lambda self, lookback_days: list(SYNC_DATES)
    service = WideTableSyncService()
    result = service.sync_multi_dates(wide_table_name=wide_table, lookback_days=len(SYNC_DATES))
    ctx["extra"]["sync_result"] = result
    return [
        ("fraudhunter_wide_table_snapshot", "wide_table_name, version_hash, etl_date"),
        ("fraudhunter_wide_table_version", "wide_table_name, version_hash"),
    ]


def _sync_full(ctx, pyspark: bool):
    from models.db_base import get_db_session
    from utils.config import settings

    settings.pyspark_enabled = pyspark
    md = dep_metadata(include_realtime=False)
    with get_db_session() as db:
        seed_common(db)
        seed_version(db, "dep_acct_wide_table", VH_DEP_NEW, md, "target", datetime(2026, 10, 1))
        # 10-09 / 10-08 就绪，10-07 未就绪（覆盖跳过分支）
        _seed_progress(db, md, SYNC_DATES[:2])
    return _run_sync(ctx)


def scenario_sync_full_jdbc(ctx):
    """离线同步：无可复用历史分区 → 全量同步（JDBC 模式）"""
    return _sync_full(ctx, pyspark=False)


def scenario_sync_full_pyspark(ctx):
    """离线同步：全量同步（PySpark 模式）"""
    return _sync_full(ctx, pyspark=True)


def scenario_sync_delta(ctx):
    """离线同步：版本变化（新增/改版/删除指标）+ 可复用旧分区 → 指标列级增量"""
    from models.db_base import get_db_session
    from utils.config import settings

    settings.pyspark_enabled = False
    pg = ctx["pg"]
    old_md = dep_metadata(include_realtime=False, codes={
        "i_dep_acct_no_offline_00001", "i_dep_acct_no_offline_00002", "i_dep_acct_no_offline_00007",
        "i_dep_acct_no_offline_00010", "i_dep_acct_no_offline_00011",
    })
    new_md = dep_metadata(include_realtime=False, codes={
        "i_dep_acct_no_offline_00001", "i_dep_acct_no_offline_00002", "i_dep_acct_no_offline_00007",
        "i_dep_acct_no_offline_00010", "i_dep_acct_no_offline_00012",
    })
    new_md["4"]["version"] = 2  # 00010 改版；00011 删除；00012 新增
    with get_db_session() as db:
        seed_common(db)
        seed_version(db, "dep_acct_wide_table", VH_DEP_OLD, old_md, "current", datetime(2026, 9, 1))
        seed_version(db, "dep_acct_wide_table", VH_DEP_NEW, new_md, "target", datetime(2026, 10, 1))
        for d in SYNC_DATES:
            seed_snapshot(db, "dep_acct_wide_table", VH_DEP_OLD, d, f"dep_acct_wide_table_{VH_DEP_OLD[:8]}")
        _seed_progress(db, new_md, SYNC_DATES)
    # 10-09/10-08 旧分区存在且有数据；10-07 旧分区为空（覆盖全量回退分支）
    pg.tables[f"dep_acct_wide_table_{VH_DEP_OLD[:8]}_20261009"] = 120
    pg.tables[f"dep_acct_wide_table_{VH_DEP_OLD[:8]}_20261008"] = 80
    pg.tables[f"dep_acct_wide_table_{VH_DEP_OLD[:8]}_20261007"] = 0
    return _run_sync(ctx)


def scenario_sync_unchanged(ctx):
    """离线同步：指标完全未变化 + 可复用旧分区 → 跳过；已有 ready 快照 → 跳过"""
    from models.db_base import get_db_session
    from utils.config import settings

    settings.pyspark_enabled = False
    pg = ctx["pg"]
    md = dep_metadata(include_realtime=False)
    with get_db_session() as db:
        seed_common(db)
        seed_version(db, "dep_acct_wide_table", VH_DEP_OLD, md, "current", datetime(2026, 9, 1))
        seed_version(db, "dep_acct_wide_table", VH_DEP_NEW, md, "target", datetime(2026, 10, 1))
        for d in SYNC_DATES:
            seed_snapshot(db, "dep_acct_wide_table", VH_DEP_OLD, d, f"dep_acct_wide_table_{VH_DEP_OLD[:8]}")
        # 10-07 新版本已有 ready 快照
        seed_snapshot(db, "dep_acct_wide_table", VH_DEP_NEW, date(2026, 10, 7),
                      f"dep_acct_wide_table_{VH_DEP_NEW[:8]}")
        _seed_progress(db, md, SYNC_DATES)
    for d in SYNC_DATES:
        pg.tables[f"dep_acct_wide_table_{VH_DEP_OLD[:8]}_{d.strftime('%Y%m%d')}"] = 50
    return _run_sync(ctx)


SCENARIOS = {
    "realtime": scenario_realtime,
    "backtest": scenario_backtest,
    "indicator_query": scenario_indicator_query,
    "sync_full_jdbc": scenario_sync_full_jdbc,
    "sync_full_pyspark": scenario_sync_full_pyspark,
    "sync_delta": scenario_sync_delta,
    "sync_unchanged": scenario_sync_unchanged,
}

# 线程并发产生的事件（实时任务子任务并发）顺序不确定，对比前排序
_ORDER_INSENSITIVE = {"realtime"}


def forbid_duckdb():
    """PG 模式守卫：运行期任何 import duckdb / 取 DuckDB 会话 / 构造 DuckDB 存储都直接失败

    在 services 包初始化之后生效（平台通用查询引擎模块级 import duckdb 不在本守卫范围），
    检查的是 PG 业务路径中的惰性导入与 DuckDB 执行入口。
    """
    sys.modules["duckdb"] = None  # 之后的 import duckdb 抛 ImportError

    def _forbidden(*_a, **_k):
        raise AssertionError("PG 模式下不应进入 DuckDB 执行路径")

    from services.fraudhunter.wide_table_service.store import query_router
    from services.fraudhunter.wide_table_service.store import duckdb_parquet_store

    query_router.get_query_session = _forbidden
    query_router.DuckQuerySession.__init__ = _forbidden
    duckdb_parquet_store.DuckdbParquetStore.__init__ = _forbidden


def run_scenario(name, forbid=False):
    # 按应用启动的导入顺序先初始化 services 包（直接导入 utils.analyze_db_utils 会触发循环导入）
    import services  # noqa: F401

    if forbid:
        forbid_duckdb()

    engine = install_sqlite()
    pg = FakePG()
    install_fake_pg(pg)
    install_fake_spark(pg)
    ctx = {"pg": pg, "extra": {}}
    tables = SCENARIOS[name](ctx)
    events = pg.events
    if name in _ORDER_INSENSITIVE:
        events = sorted(events, key=lambda e: json.dumps(e, ensure_ascii=False, sort_keys=True))
    return {
        "events": events,
        "db": dump_tables(engine, tables),
        "extra": _jsonable(ctx["extra"]),
        "storage_backends": _storage_backends(engine),
    }


def _storage_backends(engine):
    """分支新增列的取值（main 无此列时为 None），由测试单独断言全部为 postgresql"""
    from sqlalchemy import inspect, text

    cols = [c["name"] for c in inspect(engine).get_columns("fraudhunter_wide_table_snapshot")]
    if "storage_backend" not in cols:
        return None
    with engine.connect() as conn:
        return sorted({r[0] for r in conn.execute(text(
            "SELECT storage_backend FROM fraudhunter_wide_table_snapshot"
        ))})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend-root", required=True)
    parser.add_argument("--scenario", required=True, choices=sorted(SCENARIOS))
    parser.add_argument("--out", required=True)
    parser.add_argument("--write-config", action="store_true")
    parser.add_argument("--forbid-duckdb", action="store_true",
                        help="启用 PG 模式守卫（仅当前分支可用）")
    args = parser.parse_args()

    # 规则引擎指标别名映射的遍历顺序依赖字符串哈希（main 同样如此），固定哈希种子以保证可比
    if os.environ.get("PYTHONHASHSEED") != "0":
        os.environ["PYTHONHASHSEED"] = "0"
        os.execv(sys.executable, [sys.executable, *sys.argv])

    backend_root = Path(args.backend_root).resolve()
    out_path = Path(args.out).resolve()
    os.environ["TAOSHA_CONFIG_FILE"] = str(GOLDEN_CONFIG)
    target_cfg = backend_root / "config" / "config.yaml"
    if args.write_config and not target_cfg.exists():
        shutil.copy(GOLDEN_CONFIG, target_cfg)
    os.chdir(backend_root)
    sys.path.insert(0, str(backend_root))

    result = run_scenario(args.scenario, forbid=args.forbid_duckdb)
    out_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=1, sort_keys=True, default=str),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
