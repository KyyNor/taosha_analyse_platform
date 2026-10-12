"""
阶段 10：淘沙内部存储接口 + DS delegate 模式（docs/fraudhunter_offline_dual_store_plan.md 第七章）

检查项在 checks.py 中（真实 import 链，独立子进程运行，避免与其它用 fake 包加载
模块的测试互相污染 sys.modules）。本文件一次性运行全部检查并逐项断言：
- 服务端 ParquetOpsService：名称白名单/路径越界、probe/pull/merge/cleanup、错误码翻译、文件锁 BUSY；
- 路由：token 未配置 503 / 错误 401 / 正确 200，业务错误码映射，路由为同步 def；
- DS 客户端：BUSY 退避重试、请求头与 URL、错误映射、未配置 endpoint；
- DS delegate 全链路同步（禁止本地文件系统与 duckdb）：全量、增量（probe 找到基准）、
  对象范围变化回退全量、版本无变化零拷贝、服务端路径与快照记录不一致时不复用。
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

_here = Path(__file__).resolve().parent


@pytest.fixture(scope="module")
def check_results(tmp_path_factory):
    out = tmp_path_factory.mktemp("delegate") / "results.json"
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
def test_delegate_check(check_results, name):
    assert name in check_results, f"检查项 {name} 未执行"
    assert check_results[name] == "ok", check_results[name]
