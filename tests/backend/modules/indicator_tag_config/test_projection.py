"""命中记录指标值展示：编码→indicator_data 投影纯逻辑测试。

被测逻辑位置：
    backend/domain/indicator_tag_display.py

背景：命中记录 indicator_data JSON 的 key 是命中时刻的指标显示名
（实时指标带 [实时] 前缀），非指标编码；投影需按指标类型决定候选
key 优先级并容忍改名/缺失。
"""

import sys
from pathlib import Path

_backend_root = Path(__file__).parents[4] / "backend"
sys.path.insert(0, str(_backend_root))

from domain.indicator_tag_display import (
    REALTIME_INDICATOR_PREFIX,
    dedupe_preserve_order,
    find_unknown_codes,
    get_indicator_json_keys,
    project_indicator_values,
)


def test_realtime_indicator_prefers_prefixed_key():
    keys = get_indicator_json_keys("年日均", "realtime")
    assert keys == [f"{REALTIME_INDICATOR_PREFIX}年日均", "年日均"]


def test_offline_indicator_prefers_plain_key():
    keys = get_indicator_json_keys("贷款余额", "offline")
    assert keys == ["贷款余额", f"{REALTIME_INDICATOR_PREFIX}贷款余额"]


def test_project_takes_priority_key_first():
    indicators = [{"indicator_code": "i_x", "indicator_name": "年日均", "indicator_type": "realtime"}]
    data = {f"{REALTIME_INDICATOR_PREFIX}年日均": 100, "年日均": 999}
    assert project_indicator_values(data, indicators) == {"i_x": 100}


def test_project_falls_back_to_plain_key_for_realtime():
    """历史数据可能缺失 [实时] 前缀，需回退裸名称。"""
    indicators = [{"indicator_code": "i_x", "indicator_name": "年日均", "indicator_type": "realtime"}]
    data = {"年日均": 999}
    assert project_indicator_values(data, indicators) == {"i_x": 999}


def test_project_missing_indicator_is_none():
    indicators = [
        {"indicator_code": "i_x", "indicator_name": "年日均", "indicator_type": "realtime"},
        {"indicator_code": "i_y", "indicator_name": "已改名指标", "indicator_type": "offline"},
    ]
    data = {f"{REALTIME_INDICATOR_PREFIX}年日均": 1.5, "旧名称": 2}
    assert project_indicator_values(data, indicators) == {"i_x": 1.5, "i_y": None}


def test_project_handles_none_data():
    indicators = [{"indicator_code": "i_x", "indicator_name": "年日均", "indicator_type": "offline"}]
    assert project_indicator_values(None, indicators) == {"i_x": None}


def test_project_keeps_config_order():
    indicators = [
        {"indicator_code": "i_y", "indicator_name": "贷款余额", "indicator_type": "offline"},
        {"indicator_code": "i_x", "indicator_name": "年日均", "indicator_type": "realtime"},
    ]
    data = {"贷款余额": 10, f"{REALTIME_INDICATOR_PREFIX}年日均": 20}
    assert list(project_indicator_values(data, indicators).keys()) == ["i_y", "i_x"]


def test_dedupe_preserve_order():
    assert dedupe_preserve_order(["b", "a", "b", "", None, "a"]) == ["b", "a"]
    assert dedupe_preserve_order([]) == []


def test_find_unknown_codes():
    assert find_unknown_codes(["a", "b", "ghost"], ["a", "b"]) == ["ghost"]
    assert find_unknown_codes(["a", "a"], ["a"]) == []
