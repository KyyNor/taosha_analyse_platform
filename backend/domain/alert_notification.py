"""告警通知相关的纯领域逻辑。"""

from typing import Any, List, Optional


DEFAULT_CONTROL_RES_ABS = "武汉分行监测系统"
VICTIM_CONTROL_RES_ABS = "武汉分行监测系统(分行受害人保护)"


def merge_notification_targets(
    branch_notice_no: Optional[str],
    cm_targets: List[str],
    fin_targets: List[str],
) -> str:
    """合并三类通知号，过滤空值、去重并保持首次出现顺序。"""
    all_sources = (
        ([branch_notice_no] if branch_notice_no else [])
        + list(cm_targets)
        + list(fin_targets)
    )
    targets = [
        item.strip()
        for source in all_sources
        for item in str(source).split(",")
        if item.strip()
    ]
    return ",".join(dict.fromkeys(targets))


def normalize_customer_no(value: Any) -> Optional[str]:
    """标准化指标中的客户号，并过滤常见的伪空值。"""
    if value is None:
        return None

    normalized = str(value).strip()
    if not normalized or normalized.casefold() in {"none", "null"}:
        return None
    return normalized


def resolve_control_res_abs(hit_model_names: Optional[List[str]]) -> str:
    """根据命中模型名称生成管控接口的监管摘要标识。"""
    if any("受害人" in str(name) for name in (hit_model_names or [])):
        return VICTIM_CONTROL_RES_ABS
    return DEFAULT_CONTROL_RES_ABS
