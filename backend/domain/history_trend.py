"""历史趋势相关的纯领域校验。"""

from datetime import date, datetime


def validate_history_trend_period(
    start_date: str,
    end_date: str,
) -> tuple[date, date, int]:
    """解析并校验历史趋势日期范围。"""
    try:
        parsed_start = datetime.strptime(start_date, "%Y-%m-%d").date()
        parsed_end = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(
            f"日期格式无效，应为 YYYY-MM-DD，当前值不合法: {exc}"
        ) from exc

    span_days = (parsed_end - parsed_start).days
    if span_days < 0:
        raise ValueError("开始日期不能晚于结束日期")
    if span_days > 180:
        raise ValueError("时间跨度不能超过180天")
    return parsed_start, parsed_end, span_days
