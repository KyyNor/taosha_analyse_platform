"""
回测 duckdb_mode 判定防回归守卫

背景（双存储改造 review 发现）：
回测 SQL 会 JOIN 四张表 —— 当天/前一天的 dep 宽表、前一天的 cust 宽表，
以及「模型引用客户实时指标时」当天的 cust 宽表。历史实现在判定执行引擎时
只传了前两张离线快照：

    duckdb_mode = query_router.requires_duckdb(
        dep_acct_offline_result, cust_offline_result
    )

于是「离线两张都是 PG、只有当天 cust 是 duckdb」的混合后端组合下
duckdb_mode 判为 False，走 PG 执行器，但 cust 的表引用已是
read_parquet(...)，PG 直接报函数不存在。

修复：改为把本次 SQL 实际 JOIN 的全部快照一次性交给
query_router.resolve_offline_table_refs()，由它按全量快照判定一次再统一
生成引用 —— 与实时预警任务（realtime_indicator_job）同源。

本文件两类测试：
1. 守护测试：回测路径不得再出现手写的部分快照判定（防止改回旧写法）；
2. 行为测试：用真实 query_router 覆盖「只有可选快照是 duckdb」的组合。
"""

import importlib.util
import re
import sys
import types
from datetime import date
from pathlib import Path

import pytest

_backend_root = Path(__file__).parents[4] / "backend"

_MODEL_EXECUTOR = _backend_root / "services/fraudhunter/model_service/model_executor.py"


def _load_query_router(monkeypatch):
    """加载真实 query_router（只 stub 其两个外部依赖 utils.config / utils.logger）"""
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
    monkeypatch.setitem(sys.modules, "utils.config", config_module)
    monkeypatch.setitem(sys.modules, "utils.logger", logger_module)

    spec = importlib.util.spec_from_file_location(
        "query_router_for_backtest_guard",
        _backend_root / "services/fraudhunter/wide_table_service/store/query_router.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _snap(backend, wide_table, etl_date, parquet_path=None, version_hash="abcd1234efgh5678"):
    """构造与 VersionSelectionResult 同构的快照选择结果"""
    return types.SimpleNamespace(
        wide_table_name=wide_table,
        version_hash=version_hash,
        parquet_file_path=parquet_path,
        etl_date=etl_date,
        storage_backend=backend,
    )


class TestBacktestDuckdbModeGuard:
    """守护：回测不得退回手写的部分快照判定"""

    def test_no_handwritten_partial_duckdb_mode_decision(self):
        """回测源码中不得再出现 requires_duckdb( 手写调用

        判定必须整体交给 resolve_offline_table_refs()，否则任何新增 JOIN 的
        快照都会再次漏判（本次事故即由漏判 cust_realtime 快照导致）。
        """
        text = _MODEL_EXECUTOR.read_text(encoding="utf-8")
        offending = [
            f"{i}: {line.strip()}"
            for i, line in enumerate(text.splitlines(), start=1)
            if re.search(r'^[^#]*\brequires_duckdb\s*\(', line)
        ]
        assert not offending, (
            "回测路径出现手写的 requires_duckdb 判定（须改用 "
            "query_router.resolve_offline_table_refs 按全部 JOIN 快照统一判定）:\n"
            + "\n".join(offending)
        )

    def test_backtest_uses_shared_table_ref_resolution(self):
        """回测路径确实走公共表引用解析（与实时预警任务同源）"""
        text = _MODEL_EXECUTOR.read_text(encoding="utf-8")
        assert "resolve_offline_table_refs" in text, "回测未使用公共表引用解析"
        assert "joined_snapshots" in text, "回测未按 SQL 实际 JOIN 的快照集合构造判定输入"


class TestBacktestDuckdbModeBehaviour:
    """行为：只有可选快照是 duckdb 时也必须切到 DuckDB 执行"""

    def test_only_cust_realtime_is_duckdb_switches_engine(self, monkeypatch):
        """回归场景：离线两张是 PG、当天 cust 是 duckdb → duckdb_mode 必须为 True

        修复前这里会判成 False，read_parquet 引用落到 PG 执行引擎上报错。
        """
        qr = _load_query_router(monkeypatch)
        today, yesterday = date(2026, 10, 15), date(2026, 10, 14)

        refs, duckdb_mode = qr.resolve_offline_table_refs({
            "dep_acct_realtime": _snap("postgresql", "dep_acct_wide_table", today),
            "dep_acct_offline": _snap("postgresql", "dep_acct_wide_table", yesterday),
            "cust_offline": _snap("postgresql", "cust_wide_table", yesterday),
            "cust_realtime": _snap(
                "duckdb", "cust_wide_table", today,
                parquet_path="/data/wt/cust_wide_table_abcd1234",
            ),
        })

        assert duckdb_mode is True
        assert refs["cust_realtime"].startswith(
            "read_parquet('/data/wt/cust_wide_table_abcd1234/"
        )
        # 同一判定下 PG 侧表必须补 pg_rt 前缀，否则 DuckDB 引擎下找不到表
        assert refs["dep_acct_offline"].startswith("pg_rt.public.dep_acct_wide_table_")
        assert refs["cust_offline"].startswith("pg_rt.public.cust_wide_table_")

    def test_optional_cust_realtime_excluded_when_model_does_not_use_it(self, monkeypatch):
        """模型未引用客户实时指标时，cust_realtime 不参与 JOIN 也不参与判定"""
        qr = _load_query_router(monkeypatch)
        today, yesterday = date(2026, 10, 15), date(2026, 10, 14)

        snapshots = {
            "dep_acct_realtime": _snap("postgresql", "dep_acct_wide_table", today),
            "dep_acct_offline": _snap("postgresql", "dep_acct_wide_table", yesterday),
            "cust_offline": _snap("postgresql", "cust_wide_table", yesterday),
        }
        refs, duckdb_mode = qr.resolve_offline_table_refs(snapshots)

        assert duckdb_mode is False
        assert "cust_realtime" not in refs
        # 全 PG 时保持裸表名，现状行为不变
        assert refs["dep_acct_offline"] == "dep_acct_wide_table_abcd1234efgh5678_20261014"

    def test_all_duckdb_still_uses_parquet_globs(self, monkeypatch):
        """全 duckdb 组合：全部引用为 read_parquet（正向行为未回退）"""
        qr = _load_query_router(monkeypatch)
        today = date(2026, 10, 15)

        refs, duckdb_mode = qr.resolve_offline_table_refs({
            "dep_acct_realtime": _snap(
                "duckdb", "dep_acct_wide_table", today,
                parquet_path="/data/wt/dep_acct_wide_table_11112222",
            ),
            "cust_offline": _snap(
                "duckdb", "cust_wide_table", today,
                parquet_path="/data/wt/cust_wide_table_33334444",
            ),
        })

        assert duckdb_mode is True
        assert refs["dep_acct_realtime"].startswith(
            "read_parquet('/data/wt/dep_acct_wide_table_11112222/etl_date=2026-10-15/"
        )
        assert "pg_rt" not in refs["dep_acct_realtime"]

    def test_duckdb_snapshot_without_parquet_path_falls_back_to_pg_ref(self, monkeypatch):
        """防御：duckdb 快照缺 parquet_file_path 时退回 PG 分区引用（不产生坏 SQL）"""
        qr = _load_query_router(monkeypatch)
        today = date(2026, 10, 15)

        refs, duckdb_mode = qr.resolve_offline_table_refs({
            "cust_offline": _snap("duckdb", "cust_wide_table", today, parquet_path=None),
        })

        # duckdb_mode 仍为 True（由快照后端决定），引用退回 pg_rt PG 分区表
        assert duckdb_mode is True
        assert refs["cust_offline"] == "pg_rt.public.cust_wide_table_abcd1234efgh5678_20261015"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
