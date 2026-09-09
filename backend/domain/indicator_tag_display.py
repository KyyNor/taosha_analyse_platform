"""命中记录指标值展示相关的纯领域逻辑。

命中记录 indicator_data JSON 的 key 是命中时刻的指标显示名
（实时指标带 [实时] 前缀），不是指标编码；本模块负责编码→候选 key
的推导、投影与配置编码校验，供 model_hit_alert_manager 与测试复用。
"""

from typing import Any, Dict, List, Optional

REALTIME_INDICATOR_PREFIX = "[实时]"


def get_indicator_json_keys(indicator_name: str, indicator_type: str) -> List[str]:
    """返回指标在 indicator_data 中的候选 key，按指标类型决定优先级。

    实时指标优先取带 [实时] 前缀的 key，离线指标优先取裸名称；
    两种都尝试以兼容指标类型变更或历史数据前缀缺失的情况。
    """
    plain = indicator_name
    prefixed = f"{REALTIME_INDICATOR_PREFIX}{indicator_name}"
    if indicator_type == "realtime":
        return [prefixed, plain]
    return [plain, prefixed]


def project_indicator_values(
    indicator_data: Optional[Dict[str, Any]],
    indicators: List[Dict[str, str]],
) -> Dict[str, Any]:
    """按指标元数据列表从 indicator_data 投影出 {indicator_code: value}。

    指标未写入该记录（如命中时指标尚未上线、指标改名）时值为 None。
    """
    data = indicator_data or {}
    result: Dict[str, Any] = {}
    for meta in indicators:
        value = None
        for key in get_indicator_json_keys(meta["indicator_name"], meta["indicator_type"]):
            if key in data:
                value = data[key]
                break
        result[meta["indicator_code"]] = value
    return result


def dedupe_preserve_order(codes: List[str]) -> List[str]:
    """去重并保持顺序，忽略空值。"""
    seen = set()
    ordered = []
    for code in codes:
        if code and code not in seen:
            seen.add(code)
            ordered.append(code)
    return ordered


def find_unknown_codes(codes: List[str], known_codes: List[str]) -> List[str]:
    """返回不存在于 known_codes 中的编码（用于配置保存前校验）。"""
    known = set(known_codes)
    return [code for code in dedupe_preserve_order(codes) if code not in known]
