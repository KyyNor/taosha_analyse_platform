"""
阶段4：实时任务 DuckDB 模式的 SQL 引用改写

对应 docs/fraudhunter_offline_dual_store_plan.md 阶段4（实时任务路由）：
- duckdb 模式下实时流水表 realtime_oss_inct_new 补 pg_rt 附件别名前缀；
- 已带前缀/带库名前缀的引用不被二次改写；
- 离线表占位符替换为 read_parquet 引用（由调用方传入）。

_execute_single_task 依赖线程池外的执行器，此处仅验证其纯 SQL 改写逻辑：
将改写规则复刻为本地函数与生产正则保持一致（同 test_compute_half_hour_slot 的镜像策略）。
"""

import re
import sys
from pathlib import Path

import pytest

_backend_root = Path(__file__).parents[4] / "backend"
sys.path.insert(0, str(_backend_root))

# 与生产代码 _execute_single_task 中的改写正则逐字一致（改动生产正则时须同步）
PROD_PATTERN = r'(?<![.\w])realtime_oss_inct_new\b'


def _rewrite_txn_table(sql: str) -> str:
    return re.sub(PROD_PATTERN, 'pg_rt.public.realtime_oss_inct_new', sql)


class TestTxnTableRewrite:
    def test_bare_reference_prefixed(self):
        assert _rewrite_txn_table("SELECT * FROM realtime_oss_inct_new WHERE d=1") == \
            "SELECT * FROM pg_rt.public.realtime_oss_inct_new WHERE d=1"

    def test_already_prefixed_not_double_prefixed(self):
        sql = "SELECT * FROM pg_rt.public.realtime_oss_inct_new"
        assert _rewrite_txn_table(sql) == sql

    def test_schema_qualified_not_rewritten(self):
        sql = "SELECT * FROM public.realtime_oss_inct_new"
        assert _rewrite_txn_table(sql) == sql

    def test_similar_names_not_rewritten(self):
        sql = "SELECT * FROM realtime_oss_inct_new_v2 UNION ALL SELECT * FROM xrealtime_oss_inct_new"
        result = _rewrite_txn_table(sql)
        assert "pg_rt.public.realtime_oss_inct_new_v2" not in result
        assert "pg_rt.public.xrealtime_oss_inct_new" not in result

    def test_multiple_occurrences_all_rewritten(self):
        sql = "SELECT * FROM realtime_oss_inct_new a JOIN realtime_oss_inct_new b ON a.x=b.x"
        assert _rewrite_txn_table(sql).count("pg_rt.public.realtime_oss_inct_new") == 2


class TestProdPatternAlive:
    def test_pattern_matches_prod_source(self):
        """生产代码中的正则与本测试保持一致（防漂移）"""
        source = (
            _backend_root / "services" / "scheduler" / "jobs" / "realtime_indicator_job.py"
        ).read_text(encoding="utf-8")
        assert "r'(?<![.\\w])realtime_oss_inct_new\\b'" in source
