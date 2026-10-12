"""
受害人预警

1. 淘沙后端（实时指标任务步骤3之后）：从本次执行生成的告警管控记录中筛选
   "命中模型名称含关键字 + alert_status=sent + 未执行管控" 的账号，写入受害人预警记录（状态 new），
   同一账号同一记录日期只写一次；提交后逐条调用 DS 任务启动接口，传入告警ID。
2. DS 任务（scheduler/jobs/victim_alert_send_job.py）：按告警ID读取记录，调用下游服务，
   成功置 sent，失败置 error 并记录错误内容。

接口契约（占位，按实际对接修改 _post_trigger / _post_send / _is_send_success）：
- 触发 DS：POST {trigger_api_url}  JSON {"alert_id": "<32位md5>"}，HTTP 2xx 即成功
- 下游服务：POST {send_api_url}    JSON domain.victim_alert.build_send_payload() 的全部字段，
  HTTP 2xx 且响应 JSON 的 code == "00000" 即成功
"""

from datetime import date
from typing import List, Optional, Tuple

import requests
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from domain.victim_alert import (
    STATUS_ERROR,
    STATUS_NEW,
    STATUS_SENT,
    build_send_payload,
    compute_alert_id,
    is_victim_alert,
)
from models.fraudhunter.model_execution_tracking import FraudHunterModelAlertControlRecord
from models.fraudhunter.victim_alert_record import FraudHunterVictimAlertRecord
from utils.config import settings
from utils.logger import logger

SEND_SUCCESS_CODE = '00000'
_MESSAGE_MAX_LENGTH = 2000


def collect_victim_alerts(db: Session, execution_id: int, record_date: date,
                          keyword: Optional[str] = None) -> List[FraudHunterVictimAlertRecord]:
    """筛选本次执行的受害人告警并入库（状态 new），返回新增记录；调用方负责提交"""
    keyword = keyword or settings.fraudhunter_victim_alert_model_name_keyword
    control_records = db.query(FraudHunterModelAlertControlRecord).filter(
        FraudHunterModelAlertControlRecord.execution_id == execution_id,
        FraudHunterModelAlertControlRecord.record_date == record_date,
        FraudHunterModelAlertControlRecord.alert_status == 'sent',
    ).order_by(FraudHunterModelAlertControlRecord.id).all()

    seen_accounts = {
        account_id for (account_id,) in db.query(FraudHunterVictimAlertRecord.account_id).filter(
            FraudHunterVictimAlertRecord.record_date == record_date
        )
    }

    created = []
    for control in control_records:
        if control.account_id in seen_accounts:
            continue
        if not is_victim_alert(control.hit_model_names, control.alert_status, control.control_status, keyword):
            continue
        hit_time = (control.alert_time or control.created_at).replace(microsecond=0)
        record = FraudHunterVictimAlertRecord(
            alert_id=compute_alert_id(control.account_id, control.hit_model_ids, hit_time),
            account_id=control.account_id,
            hit_model_ids=list(control.hit_model_ids or []),
            hit_model_names=list(control.hit_model_names or []),
            hit_time=hit_time,
            record_date=record_date,
            status=STATUS_NEW,
        )
        try:
            with db.begin_nested():
                db.add(record)
        except IntegrityError:
            # 唯一约束兜底：同账号同日期已存在（如并发写入）
            logger.info(f"[受害人预警] 账号当日已有记录，跳过: account_id={control.account_id}")
            seen_accounts.add(control.account_id)
            continue
        seen_accounts.add(control.account_id)
        created.append(record)
        logger.info(f"[受害人预警] 新建记录: alert_id={record.alert_id}, account_id={record.account_id}, "
                    f"models={record.hit_model_names}")
    return created


def _post_trigger(alert_id: str) -> None:
    """调用 DS 任务启动接口；失败抛异常"""
    url = settings.fraudhunter_victim_alert_trigger_api_url
    if not url:
        raise RuntimeError("未配置 fraudhunter.victim_alert.trigger_api_url")
    response = requests.post(url, json={'alert_id': alert_id},
                             timeout=settings.fraudhunter_victim_alert_timeout_seconds)
    response.raise_for_status()


def _post_send(payload: dict) -> requests.Response:
    url = settings.fraudhunter_victim_alert_send_api_url
    if not url:
        raise RuntimeError("未配置 fraudhunter.victim_alert.send_api_url")
    return requests.post(url, json=payload, timeout=settings.fraudhunter_victim_alert_timeout_seconds)


def _is_send_success(response: requests.Response) -> Tuple[bool, Optional[str]]:
    """下游响应判定：HTTP 2xx 且 code == 00000；失败时返回错误内容"""
    if not response.ok:
        return False, f"HTTP {response.status_code}: {response.text[:500]}"
    try:
        body = response.json()
    except ValueError:
        return False, f"响应不是 JSON: {response.text[:500]}"
    code = str(body.get('code')) if isinstance(body, dict) else None
    if code != SEND_SUCCESS_CODE:
        return False, f"下游返回失败: {str(body)[:500]}"
    return True, None


def _truncate(message: str) -> str:
    return message[:_MESSAGE_MAX_LENGTH]


def trigger_victim_alerts(db: Session, records: List[FraudHunterVictimAlertRecord]) -> int:
    """逐条触发 DS 任务；触发失败的记录置 error。记录必须已提交（DS 任务会读库）。返回成功数"""
    success = 0
    for record in records:
        try:
            _post_trigger(record.alert_id)
            success += 1
            logger.info(f"[受害人预警] 已触发 DS 任务: alert_id={record.alert_id}")
        except Exception as e:
            logger.error(f"[受害人预警] 触发 DS 任务失败: alert_id={record.alert_id}, error={e}")
            record.status = STATUS_ERROR
            record.message = _truncate(f"触发DS任务失败: {e}")
            db.commit()
    return success


def process_victim_alerts(db: Session, execution_id: int, record_date: date) -> None:
    """实时任务步骤4入口：入库 → 提交 → 触发 DS。任何异常只记日志，不影响实时任务"""
    if not settings.fraudhunter_victim_alert_enabled:
        return
    try:
        records = collect_victim_alerts(db, execution_id, record_date)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"[受害人预警] 入库失败: execution_id={execution_id}, error={e}", exc_info=True)
        return
    if not records:
        return
    try:
        success = trigger_victim_alerts(db, records)
        logger.info(f"[受害人预警] 本次新建 {len(records)} 条，触发成功 {success} 条")
    except Exception as e:
        db.rollback()
        logger.error(f"[受害人预警] 触发异常: execution_id={execution_id}, error={e}", exc_info=True)


SEND_OK = 'sent'
SEND_SKIPPED = 'skipped'
SEND_FAILED = 'failed'
SEND_NOT_FOUND = 'not_found'


def send_victim_alert(db: Session, alert_id: str) -> Tuple[str, str]:
    """DS 任务入口：按告警ID调用下游服务并更新状态（调用方负责提交）。

    Returns:
        (结果, 说明)，结果为 SEND_OK / SEND_SKIPPED / SEND_FAILED / SEND_NOT_FOUND
    """
    record = db.query(FraudHunterVictimAlertRecord).filter(
        FraudHunterVictimAlertRecord.alert_id == alert_id
    ).first()
    if record is None:
        return SEND_NOT_FOUND, f"告警ID不存在: {alert_id}"
    if record.status == STATUS_SENT:
        return SEND_SKIPPED, f"已发送，跳过: {alert_id}"

    payload = build_send_payload({
        column.name: getattr(record, column.name) for column in FraudHunterVictimAlertRecord.__table__.columns
    })
    try:
        ok, error = _is_send_success(_post_send(payload))
    except Exception as e:
        ok, error = False, f"调用下游服务异常: {e}"

    if ok:
        record.status = STATUS_SENT
        record.message = None
        return SEND_OK, f"发送成功: {alert_id}"
    record.status = STATUS_ERROR
    record.message = _truncate(error)
    return SEND_FAILED, f"发送失败: {alert_id}, {error}"
