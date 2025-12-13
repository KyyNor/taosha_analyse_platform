#!/usr/bin/env python3
"""
生成FraudHunter模型告警与管控记录测试数据

使用方法：
    python scripts/generate_alert_control_records.py

或者在backend目录下运行：
    cd backend && python -m scripts.generate_alert_control_records
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta, date
from random import randint, choice, random
import json

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'backend'))

from models.db_base import get_db_session, create_tables
from models.fraudhunter.model_execution_tracking import (
    FraudHunterModelHitRecord,
    FraudHunterModelAlertControlRecord
)
from utils.logger import logger


# 测试数据模板
ACCOUNT_ID_PREFIXES = [
    "ACC",      # 账号前缀
    "USER",     # 用户前缀
    "CUST",     # 客户前缀
    "MEMBER"    # 会员前缀
]

MODEL_NAMES = [
    "高风险交易检测模型",
    "异常登录行为识别模型",
    "账户盗用检测模型",
    "虚假账号识别模型",
    "刷单行为检测模型",
    "薅羊毛行为识别模型",
    "恶意注册检测模型",
    "批量操作识别模型"
]

ALERT_PERSONS = [
    "张三", "李四", "王五", "赵六", "钱七",
    "孙八", "周九", "吴十", "郑一", "陈二"
]

ALERT_STATUSES = ["not_configured", "sent", "duplicate"]
CONTROL_STATUSES = ["not_configured", "executed", "duplicate"]


def generate_account_id() -> str:
    """生成随机账号ID"""
    prefix = choice(ACCOUNT_ID_PREFIXES)
    number = randint(100000, 999999)
    return f"{prefix}{number}"


def generate_indicator_data() -> dict:
    """生成随机指标数据"""
    return {
        "risk_score": round(random() * 100, 2),
        "transaction_amount": round(random() * 10000, 2),
        "transaction_count": randint(1, 100),
        "login_count": randint(1, 50),
        "device_count": randint(1, 10),
        "ip_count": randint(1, 20),
        "abnormal_time_ratio": round(random(), 2)
    }


def generate_alert_message(model_name: str, account_id: str) -> str:
    """生成告警消息"""
    return f"【风控告警】账号 {account_id} 触发 {model_name}，请及时处理。"


def generate_control_serial_number() -> str:
    """生成管控流水号"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_num = randint(1000, 9999)
    return f"CTRL{timestamp}{random_num}"


def generate_hit_records(count: int = 50) -> list:
    """
    生成命中记录

    Args:
        count: 生成记录数量

    Returns:
        生成的命中记录列表
    """
    records = []
    base_time = datetime.now() - timedelta(days=30)

    for i in range(count):
        # 随机选择1-3个模型
        num_models = randint(1, 3)
        selected_models = []
        selected_model_ids = []

        for _ in range(num_models):
            model_id = randint(1, len(MODEL_NAMES))
            if model_id not in selected_model_ids:
                selected_model_ids.append(model_id)
                selected_models.append(MODEL_NAMES[model_id - 1])

        # 生成命中时间（最近30天内的随机时间）
        random_minutes = randint(0, 30 * 24 * 60)
        hit_time = base_time + timedelta(minutes=random_minutes)

        record = FraudHunterModelHitRecord(
            account_id=generate_account_id(),
            hit_time=hit_time,
            hit_model_ids=selected_model_ids,
            hit_model_names=selected_models,
            indicator_data=generate_indicator_data()
        )

        records.append(record)

    return records


def generate_alert_control_records(hit_records: list, records_per_hit: int = 2) -> list:
    """
    为每个命中记录生成告警与管控记录

    Args:
        hit_records: 命中记录列表
        records_per_hit: 每个命中记录生成的告警管控记录数（通常等于命中的模型数）

    Returns:
        生成的告警与管控记录列表
    """
    records = []

    for hit_record in hit_records:
        # 为每个命中的模型创建一条告警管控记录
        num_models = len(hit_record.hit_model_ids)

        for i in range(num_models):
            model_id = hit_record.hit_model_ids[i]
            model_name = hit_record.hit_model_names[i]

            # 随机决定告警和管控状态
            alert_status = choice(ALERT_STATUSES)
            control_status = choice(CONTROL_STATUSES)

            # 如果有告警，生成相关字段
            alert_message = None
            alert_person = None
            alert_time = None

            if alert_status == "sent":
                alert_message = generate_alert_message(model_name, hit_record.account_id)
                alert_person = choice(ALERT_PERSONS)
                # 告警时间在命中时间后几分钟
                alert_time = hit_record.hit_time + timedelta(minutes=randint(1, 10))
            elif alert_status == "duplicate":
                alert_message = f"重复告警：{model_name}"

            # 如果有管控，生成相关字段
            control_time = None
            control_serial_number = None

            if control_status == "executed":
                # 管控时间在告警时间后（如果有告警）或命中时间后
                base_time = alert_time if alert_time else hit_record.hit_time
                control_time = base_time + timedelta(minutes=randint(5, 30))
                control_serial_number = generate_control_serial_number()

            record = FraudHunterModelAlertControlRecord(
                hit_record_id=None,  # 先不设置，保存hit_record后再设置
                account_id=hit_record.account_id,
                record_date=hit_record.hit_time.date(),
                model_id=model_id,
                model_name=model_name,
                alert_status=alert_status,
                alert_message=alert_message,
                alert_person=alert_person,
                alert_time=alert_time,
                control_status=control_status,
                control_time=control_time,
                control_serial_number=control_serial_number
            )

            records.append((hit_record, record))

    return records


def main():
    """主函数"""
    try:
        logger.info("开始生成测试数据...")

        # 确保表已创建
        create_tables()

        # 使用数据库会话
        with get_db_session() as db:
            # 1. 生成命中记录（生成60条命中记录，每条平均1.8个模型，可以产生约100条告警管控记录）
            logger.info("正在生成命中记录...")
            hit_records = generate_hit_records(count=60)

            # 保存命中记录
            db.add_all(hit_records)
            db.flush()  # 刷新以获取ID

            logger.info(f"已生成 {len(hit_records)} 条命中记录")

            # 2. 生成告警与管控记录
            logger.info("正在生成告警与管控记录...")
            alert_control_data = generate_alert_control_records(hit_records)

            alert_control_records = []
            for hit_record, alert_control_record in alert_control_data:
                # 设置外键关联
                alert_control_record.hit_record_id = hit_record.id
                alert_control_records.append(alert_control_record)

            # 保存告警与管控记录
            db.add_all(alert_control_records)
            db.commit()

            logger.info(f"已生成 {len(alert_control_records)} 条告警与管控记录")

            # 3. 统计信息
            logger.info("\n" + "=" * 60)
            logger.info("数据生成完成！统计信息：")
            logger.info(f"命中记录总数: {len(hit_records)}")
            logger.info(f"告警与管控记录总数: {len(alert_control_records)}")

            # 按状态统计
            alert_status_count = {}
            control_status_count = {}

            for record in alert_control_records:
                alert_status_count[record.alert_status] = alert_status_count.get(record.alert_status, 0) + 1
                control_status_count[record.control_status] = control_status_count.get(record.control_status, 0) + 1

            logger.info("\n告警状态分布：")
            for status, count in alert_status_count.items():
                logger.info(f"  {status}: {count} 条")

            logger.info("\n管控状态分布：")
            for status, count in control_status_count.items():
                logger.info(f"  {status}: {count} 条")

            logger.info("=" * 60)

            return True

    except Exception as e:
        logger.error(f"生成测试数据失败: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
