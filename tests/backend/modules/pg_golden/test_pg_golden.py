"""
PG 零影响守护（docs/fraudhunter_offline_dual_store_plan.md 阶段 8）

offline_store=postgresql（默认）时，当前分支在 PG 侧执行的全部 SQL、写入的数据形状、
MySQL 元数据最终状态必须与 main 分支逐字一致。

- harness.py 在独立子进程中运行固定场景（实时任务 step1+step2、模型回测、指标查询、
  离线同步全量 JDBC/PySpark、增量、无变化跳过），记录 FakePG 收到的 SQL 序列；
- golden/*.json 是在 main 分支上运行同一 harness 采集的基准；
- 当前分支额外启用 --forbid-duckdb：PG 路径中任何惰性 import duckdb、取 DuckDB 会话、
  构造 DuckDB 存储都会直接失败。

重新采集基准（仅当 main 上的 PG 行为有意变化时）：
    git worktree add /tmp/main_wt main
    for sc in realtime backtest indicator_query sync_full_jdbc sync_full_pyspark sync_delta sync_unchanged; do
        uv run python tests/backend/modules/pg_golden/harness.py --backend-root /tmp/main_wt/backend \\
            --write-config --scenario $sc --out tests/backend/modules/pg_golden/golden/$sc.json
    done
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

_here = Path(__file__).resolve().parent
_backend_root = _here.parents[3] / "backend"
_harness = _here / "harness.py"

SCENARIOS = [
    "realtime",
    "backtest",
    "indicator_query",
    "sync_full_jdbc",
    "sync_full_pyspark",
    "sync_delta",
    "sync_unchanged",
]


# 读路径场景：影子写模式下（both 写、未配置读后端、库里有更新的 duckdb 快照）也必须与 main 一致
READ_SCENARIOS = ["realtime", "backtest", "indicator_query"]


def _run_harness(scenario: str, out: Path, *extra: str) -> None:
    proc = subprocess.run(
        [sys.executable, str(_harness), "--backend-root", str(_backend_root),
         "--scenario", scenario, "--out", str(out), "--forbid-duckdb", *extra],
        capture_output=True, text=True, timeout=300,
    )
    if proc.returncode != 0:
        tail = "\n".join((proc.stdout + proc.stderr).splitlines()[-40:])
        pytest.fail(f"harness 场景 {scenario} 执行失败:\n{tail}")


def _load_pair(scenario, out):
    actual = json.loads(out.read_text(encoding="utf-8"))
    golden = json.loads((_here / "golden" / f"{scenario}.json").read_text(encoding="utf-8"))
    golden.pop("storage_backends")
    return actual, golden


def _assert_same(scenario, actual, golden):
    for key in ("events", "db", "extra"):
        assert actual[key] == golden[key], (
            f"场景 {scenario} 的 {key} 与 main 不一致；"
            f"运行 harness 输出 JSON 后与 golden/{scenario}.json 做 diff 定位"
        )
    assert actual.keys() == golden.keys()


@pytest.mark.parametrize("scenario", READ_SCENARIOS)
def test_shadow_write_keeps_pg_read_path(scenario, tmp_path):
    """阶段 9 验收：offline_store=both 且未配置 read_backend 时，读路径与 main 完全一致"""
    out = tmp_path / f"{scenario}.json"
    _run_harness(scenario, out, "--shadow-duckdb")
    actual, golden = _load_pair(scenario, out)
    assert actual.pop("storage_backends") == ["duckdb", "postgresql"]
    # db 快照表中多出影子 duckdb 行属预期，只对比非快照表与 SQL/结果
    actual["db"].pop("fraudhunter_wide_table_snapshot", None)
    golden["db"].pop("fraudhunter_wide_table_snapshot", None)
    _assert_same(scenario, actual, golden)


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_pg_behavior_identical_to_main(scenario, tmp_path):
    out = tmp_path / f"{scenario}.json"
    _run_harness(scenario, out)
    actual, golden = _load_pair(scenario, out)

    # 分支新增的 storage_backend 列：PG 模式下所有快照必须为 postgresql
    backends = actual.pop("storage_backends")
    assert backends in ([], ["postgresql"]), f"PG 模式出现非 postgresql 快照: {backends}"

    _assert_same(scenario, actual, golden)


def test_golden_covers_pg_paths():
    """基准本身要覆盖关键路径，防止场景退化成"空跑也一致" """
    def load(name):
        return json.loads((_here / "golden" / f"{name}.json").read_text(encoding="utf-8"))

    def sqls(name):
        return "\n".join(str(e[1]) for e in load(name)["events"])

    assert "实时模型匹配SQL" in sqls("realtime")
    assert "realtime_oss_inct_new" in sqls("realtime")
    assert "模型历史回测SQL" in sqls("backtest")
    assert "LIMIT 50 OFFSET 0" in sqls("indicator_query")
    assert "PIVOT" in sqls("sync_full_jdbc")
    assert any(e[0] == "pyspark.jdbc_write" for e in load("sync_full_pyspark")["events"])
    assert "INSERT INTO" in sqls("sync_delta")
    assert load("sync_unchanged")["extra"]["sync_result"]["details"][0]["reason"] == \
        "version_unchanged_with_reusable_base"
