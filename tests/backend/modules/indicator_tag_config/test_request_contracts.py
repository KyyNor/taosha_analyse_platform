"""命中记录指标展示配置与批量取值的请求/响应契约测试。

被测逻辑位置：
    backend/schemas/fraudhunter/alert_control_record.py
"""

import sys
from pathlib import Path

import pytest

_backend_root = Path(__file__).parents[4] / "backend"
sys.path.insert(0, str(_backend_root))

from pydantic import ValidationError

from schemas.fraudhunter.alert_control_record import (
    IndicatorTagConfigResponse,
    IndicatorTagConfigUpdateRequest,
    IndicatorValuesRequest,
    IndicatorValuesResponse,
)


def test_tag_config_update_accepts_empty_list_to_clear():
    req = IndicatorTagConfigUpdateRequest(indicator_codes=[])
    assert req.indicator_codes == []


def test_tag_config_update_rejects_over_50_codes():
    with pytest.raises(ValidationError):
        IndicatorTagConfigUpdateRequest(indicator_codes=[f"i_{n}" for n in range(51)])


def test_tag_config_response_coerces_meta_dicts():
    resp = IndicatorTagConfigResponse(indicators=[
        {"indicator_code": "i_x", "indicator_name": "年日均", "indicator_type": "realtime"},
    ])
    assert resp.indicators[0].indicator_code == "i_x"
    assert resp.indicators[0].indicator_name == "年日均"


def test_values_request_bounds():
    assert IndicatorValuesRequest(
        hit_record_ids=[1, 2], indicator_codes=["i_x"]
    ).hit_record_ids == [1, 2]

    with pytest.raises(ValidationError):
        IndicatorValuesRequest(hit_record_ids=[], indicator_codes=["i_x"])

    with pytest.raises(ValidationError):
        IndicatorValuesRequest(hit_record_ids=list(range(501)), indicator_codes=["i_x"])

    with pytest.raises(ValidationError):
        IndicatorValuesRequest(hit_record_ids=[1], indicator_codes=[])


def test_values_response_serializes_int_keys_to_strings():
    resp = IndicatorValuesResponse(values={101: {"i_x": 1.5}, 102: {"i_x": None}})
    dumped = resp.model_dump_json()
    assert '"101"' in dumped
    assert "null" in dumped
