"""
受害人预警（实时任务步骤4 + DS 发送任务）

检查项在 checks.py 中（真实 ORM 模型与服务代码 + SQLite 内存库 + 替身 HTTP，独立子进程运行）：
- 筛选：模型名称含关键字、alert_status=sent、control_status!=executed，只看本次执行；
- 入库字段、告警ID（md5(账号+模型ID逗号拼接+告警时间到秒)）、同账号同日只插一次；
- 提交后再触发 DS（DS 任务读库可见），触发失败置 error；未启用不做任何事；异常不外抛；
- DS 任务：请求体为全部字段，成功置 sent，业务失败/HTTP 失败/异常/未配置 URL 置 error，
  已发送跳过，error 可重试，退出码 0/1/2。
另含 domain.victim_alert 纯函数测试（进程内）。
"""

import json
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

import pytest

_here = Path(__file__).resolve().parent
sys.path.insert(0, str(_here.parents[3] / "backend"))

from domain.victim_alert import build_send_payload, compute_alert_id, is_victim_alert  # noqa: E402


@pytest.fixture(scope="module")
def check_results():
    proc = subprocess.run([sys.executable, str(_here / "checks.py")], capture_output=True, text=True, timeout=300)
    results = {}
    for line in proc.stdout.splitlines():
        try:
            item = json.loads(line)
        except ValueError:
            continue
        results[item["name"]] = item
    if not results:
        pytest.fail("checks.py 执行失败:\n" + "\n".join((proc.stdout + proc.stderr).splitlines()[-60:]))
    return results


def _names():
    source = (_here / "checks.py").read_text(encoding="utf-8").splitlines()
    return [source[i + 1].split("(")[0][len("def "):] for i, line in enumerate(source) if line == "@check"]


@pytest.mark.parametrize("name", _names())
def test_victim_alert_check(check_results, name):
    assert name in check_results, f"检查项 {name} 未执行"
    assert check_results[name]["ok"], check_results[name]["detail"]


def test_alert_id_is_md5_of_concatenation():
    import hashlib

    t = datetime(2026, 10, 11, 9, 30, 15, 999)
    assert compute_alert_id("6222001", [3, 12], t) == hashlib.md5("62220013,122026-10-11 09:30:15".encode()).hexdigest()
    assert compute_alert_id("6222001", [3, 12], t) != compute_alert_id("6222001", [12, 3], t)


@pytest.mark.parametrize("names,alert,control,expected", [
    (["受害人保护模型"], "sent", "not_configured", True),
    (["普通", "疑似受害人"], "sent", "duplicate", True),
    (["受害人保护模型"], "sent", "executed", False),
    (["受害人保护模型"], "duplicate", "not_configured", False),
    (["受害人保护模型"], "whitelist", "whitelist", False),
    (["涉诈模型"], "sent", "not_configured", False),
    ([], "sent", "not_configured", False),
    (None, "sent", "not_configured", False),
])
def test_is_victim_alert(names, alert, control, expected):
    assert is_victim_alert(names, alert, control) is expected


def test_custom_keyword():
    assert is_victim_alert(["老年人关怀"], "sent", None, keyword="老年人")


def test_build_send_payload_serializes_dates():
    payload = build_send_payload({
        "id": 1, "alert_id": "a", "account_id": "A1", "hit_model_ids": [1], "hit_model_names": ["受害人"],
        "hit_time": datetime(2026, 10, 11, 9, 30, 15), "record_date": date(2026, 10, 11),
        "status": "new", "message": None, "created_at": datetime.now(),
    })
    assert payload == {
        "alert_id": "a", "account_id": "A1", "hit_model_ids": [1], "hit_model_names": ["受害人"],
        "hit_time": "2026-10-11 09:30:15", "record_date": "2026-10-11", "status": "new", "message": None,
    }
