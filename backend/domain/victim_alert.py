"""受害人预警的纯领域逻辑（不依赖数据库和外部服务）。"""

import hashlib
from datetime import date, datetime
from typing import Any, Dict, Iterable, Optional

STATUS_NEW = 'new'        # 新建：实时任务已入库，等待 DS 任务发送
STATUS_SENT = 'sent'      # 已发送：DS 任务调用下游服务成功
STATUS_ERROR = 'error'    # 异常：触发 DS 或调用下游失败，原因记录在 message

STATUS_DISPLAY = {STATUS_NEW: '新建', STATUS_SENT: '已发送', STATUS_ERROR: '异常'}

DEFAULT_MODEL_NAME_KEYWORD = '受害人'

_TIME_FORMAT = '%Y-%m-%d %H:%M:%S'


def format_alert_time(alert_time: Optional[datetime]) -> str:
    """告警时间统一精确到秒（MySQL DATETIME 精度），保证告警ID与入库值一致"""
    return alert_time.strftime(_TIME_FORMAT) if alert_time else ''


def compute_alert_id(account_id: str, hit_model_ids: Iterable[Any], alert_time: Optional[datetime]) -> str:
    """告警ID = md5(账号 + 命中模型ID逗号拼接 + 告警时间)"""
    raw = f"{account_id}{','.join(str(i) for i in hit_model_ids or [])}{format_alert_time(alert_time)}"
    return hashlib.md5(raw.encode('utf-8')).hexdigest()


def is_victim_alert(hit_model_names: Iterable[Any], alert_status: Optional[str], control_status: Optional[str],
                    keyword: str = DEFAULT_MODEL_NAME_KEYWORD) -> bool:
    """命中模型名称含关键字，告警已发送，且未执行管控"""
    if alert_status != 'sent' or control_status == 'executed':
        return False
    return any(keyword in str(name) for name in hit_model_names or [])


def build_send_payload(record: Dict[str, Any]) -> Dict[str, Any]:
    """下游服务请求体：新表的全部业务字段（日期时间转字符串）"""
    record_date = record.get('record_date')
    return {
        'alert_id': record.get('alert_id'),
        'account_id': record.get('account_id'),
        'hit_model_ids': list(record.get('hit_model_ids') or []),
        'hit_model_names': list(record.get('hit_model_names') or []),
        'hit_time': format_alert_time(record.get('hit_time')),
        'record_date': record_date.isoformat() if isinstance(record_date, date) else (record_date or ''),
        'status': record.get('status'),
        'message': record.get('message'),
    }
