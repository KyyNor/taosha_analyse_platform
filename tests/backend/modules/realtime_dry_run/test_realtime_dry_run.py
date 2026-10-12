"""
阶段 12：实时预警试跑（docs/fraudhunter_offline_dual_store_plan.md 第七章）

检查项在 checks.py 中（真实 import 链 + SQLite 元数据库 + FakePG，独立子进程运行）：
- PG 试跑生成的模型匹配 SQL 与线上 step2（pg_golden 基准）逐字一致；
- 全程无写入：执行记录/命中/告警/管控表与快照表行数不变，无 PG 写操作，不调用告警管理器；
- duckdb 试跑走 DuckDB 会话（read_parquet + pg_rt 实时表 + DuckDB 方言），不在 PG 执行；
- both 差异：仅 PG / 仅 DuckDB / 字段值超容差；完全一致时 identical；
- 强制后端无快照时报错且不回退；两侧快照不一致时告警；etl_date 与模型过滤；非法输入；
- 接口（鉴权、截断、不返回全量明细、同步 def）与 CLI（输出、CSV/差异导出、退出码）。
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

_here = Path(__file__).resolve().parent


@pytest.fixture(scope="module")
def check_results(tmp_path_factory):
    out = tmp_path_factory.mktemp("dry_run") / "results.json"
    proc = subprocess.run(
        [sys.executable, str(_here / "checks.py"), "--out", str(out)],
        capture_output=True, text=True, timeout=600,
    )
    if proc.returncode != 0 or not out.exists():
        pytest.fail("checks.py 执行失败:\n" + "\n".join((proc.stdout + proc.stderr).splitlines()[-60:]))
    return json.loads(out.read_text(encoding="utf-8"))


def _names():
    source = (_here / "checks.py").read_text(encoding="utf-8")
    return [line.split("(")[0][len("def "):] for line in source.splitlines()
            if line.startswith("def check_")]


@pytest.mark.parametrize("name", _names())
def test_dry_run_check(check_results, name):
    assert name in check_results, f"检查项 {name} 未执行"
    assert check_results[name] == "ok", check_results[name]
