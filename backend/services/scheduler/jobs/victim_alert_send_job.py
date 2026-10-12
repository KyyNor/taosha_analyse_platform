"""
受害人预警发送任务（DS 执行）

淘沙后端实时任务写入受害人预警记录后调用 DS 任务启动接口，DS 把告警ID作为参数传入本任务；
本任务按告警ID读取记录，POST 全部字段到下游服务（淘沙机器与下游服务不直接联通，由 DS 中转）。
成功置 sent；失败置 error 并在 message 记录错误内容。已是 sent 的记录直接跳过（DS 重跑幂等）。

用法：
    python -m services.scheduler.jobs.victim_alert_send_job --alert-id <告警ID>

退出码：0 成功或已发送；1 发送失败；2 告警ID不存在
"""

import argparse
import sys

from utils.logger import logger


def main(argv=None) -> int:
    from models.db_base import get_db_session
    from services.fraudhunter.model_service.victim_alert_service import (
        SEND_FAILED,
        SEND_NOT_FOUND,
        send_victim_alert,
    )

    parser = argparse.ArgumentParser(description='受害人预警发送任务')
    parser.add_argument('--alert-id', required=True, help='受害人预警记录的告警ID')
    args = parser.parse_args(argv)

    with get_db_session() as db:
        result, message = send_victim_alert(db, args.alert_id.strip())
    if result == SEND_NOT_FOUND:
        logger.error(f"[受害人预警] {message}")
        return 2
    if result == SEND_FAILED:
        logger.error(f"[受害人预警] {message}")
        return 1
    logger.info(f"[受害人预警] {message}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
