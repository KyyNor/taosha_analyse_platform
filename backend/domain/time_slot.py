"""调度时间槽相关的纯领域逻辑。"""

import re
from datetime import datetime


_TIMESTAMP_PATTERN = re.compile(r"^[0-9]{12}$")


def compute_half_hour_slot(full_ts: str) -> str:
    """将 YYYYMMDDHHMM 时间戳向下归整到半小时边界。"""
    if not _TIMESTAMP_PATTERN.fullmatch(full_ts):
        raise ValueError("时间戳格式必须是 YYYYMMDDHHMM")

    base_dt = datetime.strptime(full_ts, "%Y%m%d%H%M")
    floored_minute = (base_dt.minute // 30) * 30
    floored = base_dt.replace(minute=floored_minute, second=0, microsecond=0)
    return floored.strftime("%Y%m%d%H%M")
