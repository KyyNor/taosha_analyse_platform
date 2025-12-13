#!/usr/bin/env python3
"""
创建测试用的告警管控记录数据
"""

import sys
import os
from datetime import datetime, date, timedelta
from typing import List

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.db_base import get_db_session
from models.fraudhunter.model_execution_tracking import (
    FraudHunterModelHitRecord,
    FraudHunterModelAlertControlRecord
)
from models.fraudhunter.risk_control_model import FraudHunterModelDefinition
from services.fraudhunter.model_execution_service.model_hit_alert_manager import (
    ModelHitAlertManager,
    ModelHit
)
from utils.logger import logger


def create_test_models(db):
    """创建测试模型定义"""
    test_models = [
        {
            "id": 1,
            "model_name": "高风险交易模型",
            "is_send_alert_message": True,
            "is_acct_control": False,
            "description": "检测高风险交易行为"
        },
        {
            "id": 2,
            "model_name": "异常登录模型",
            "is_send_alert_message": True,
            "is_acct_control": True,
            "description": "检测异常登录行为"
        },
        {
            "id": 3,
            "model_name": "资金流向模型",
            "is_send_alert_message": False,
            "is_acct_control": False,
            "description": "分析资金流向模式"
        }
    ]
    
    for model_data in test_models:
        existing = db.query(FraudHunterModelDefinition).filter(
            FraudHunterModelDefinition.id == model_data["id"]
        ).first()
        
        if not existing:
            model = FraudHunterModelDefinition(
                id=model_data["id"],
                model_name=model_data["model_name"],
                is_send_alert_message=model_data["is_send_alert_message"],
                is_acct_control=model_data["is_acct_control"],
                description=model_data["description"],
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            db.add(model)
    
    db.commit()
    logger.info("测试模型定义创建完成")


def create_test_data(db):
    """创建测试数据"""
    manager = ModelHitAlertManager(db)
    
    # 测试账号列表
    test_accounts = ["ACC001", "ACC002", "ACC003", "ACC004", "ACC005"]
    
    # 创建过去7天的测试数据
    for days_ago in range(7):
        test_date = datetime.now() - timedelta(days=days_ago)
        
        for i, account_id in enumerate(test_accounts):
            # 为每个账号创建1-3条命中记录
            num_hits = (i % 3) + 1
            
            for hit_idx in range(num_hits):
                # 随机选择命中的模型
                if hit_idx == 0:
                    hit_models = [ModelHit(1, "高风险交易模型")]
                elif hit_idx == 1:
                    hit_models = [ModelHit(2, "异常登录模型")]
                else:
                    hit_models = [
                        ModelHit(1, "高风险交易模型"),
                        ModelHit(3, "资金流向模型")
                    ]
                
                # 创建指标数据
                indicator_data = {
                    "transaction_amount": 10000 + (i * 1000) + (hit_idx * 500),
                    "risk_score": 0.7 + (i * 0.05) + (hit_idx * 0.1),
                    "login_location": f"Location_{i}_{hit_idx}",
                    "device_fingerprint": f"Device_{account_id}_{hit_idx}",
                    "transaction_count": 5 + hit_idx,
                    "time_window": "1h"
                }
                
                # 创建命中记录
                hit_time = test_date.replace(
                    hour=9 + hit_idx,
                    minute=30 + (i * 10),
                    second=0,
                    microsecond=0
                )
                
                try:
                    hit_record = manager.create_hit_record(
                        account_id=account_id,
                        hit_models=hit_models,
                        indicator_data=indicator_data,
                        hit_time=hit_time
                    )
                    
                    # 处理命中记录，生成告警管控记录
                    alert_control_records = manager.hit_record_processor(hit_record)
                    
                    # 发送告警和处理管控
                    manager.send_alert_message(alert_control_records)
                    manager.process_alert_control(alert_control_records)
                    
                    logger.info(f"创建测试数据: {account_id}, {len(hit_models)}个模型, {hit_time}")
                    
                except Exception as e:
                    logger.error(f"创建测试数据失败: {e}")
                    continue
    
    db.commit()
    logger.info("测试数据创建完成")


def main():
    """主函数"""
    logger.info("开始创建测试用告警管控记录数据...")
    
    with get_db_session() as db:
        try:
            # 创建测试模型定义
            create_test_models(db)
            
            # 创建测试数据
            create_test_data(db)
            
            # 统计创建的数据
            hit_count = db.query(FraudHunterModelHitRecord).count()
            alert_count = db.query(FraudHunterModelAlertControlRecord).count()
            
            logger.info(f"测试数据创建完成！")
            logger.info(f"命中记录: {hit_count} 条")
            logger.info(f"告警管控记录: {alert_count} 条")
            
        except Exception as e:
            logger.error(f"创建测试数据失败: {e}", exc_info=True)
            db.rollback()
            raise


if __name__ == "__main__":
    main()