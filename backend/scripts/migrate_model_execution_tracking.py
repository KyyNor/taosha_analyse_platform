#!/usr/bin/env python
"""
创建模型执行跟踪系统相关表

该脚本用于创建以下表：
1. fraudhunter_hit_record - 模型运行命中记录表
2. fraudhunter_alert_control_record - 模型告警与管控记录表

使用方法：
    python backend/scripts/migrate_model_execution_tracking.py
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from models.db_base import SessionLocal, engine
from models.fraudhunter.model_execution_tracking import (
    FraudHunterModelHitRecord,
    FraudHunterModelAlertControlRecord
)
from utils.logger import logger


def check_table_exists(table_name: str) -> bool:
    """检查表是否存在"""
    try:
        with SessionLocal() as db:
            # 检查表是否存在的SQL（兼容MySQL和SQLite）
            result = db.execute(text(f"""
                SELECT COUNT(*) as count 
                FROM information_schema.tables 
                WHERE table_name = '{table_name}'
                AND table_schema = DATABASE()
            """))
            count = result.scalar()
            return count > 0
    except Exception:
        # 如果是SQLite，使用不同的查询
        try:
            with SessionLocal() as db:
                result = db.execute(text(f"""
                    SELECT COUNT(*) as count 
                    FROM sqlite_master 
                    WHERE type='table' AND name='{table_name}'
                """))
                count = result.scalar()
                return count > 0
        except Exception as e:
            logger.warning(f"无法检查表 {table_name} 是否存在: {e}")
            return False


def create_model_execution_tracking_tables():
    """创建模型执行跟踪相关表"""
    try:
        logger.info("开始创建模型执行跟踪系统表...")

        # 检查表是否已存在
        hit_record_exists = check_table_exists('fraudhunter_hit_record')
        alert_control_exists = check_table_exists('fraudhunter_alert_control_record')

        if hit_record_exists and alert_control_exists:
            logger.info("模型执行跟踪表已存在，跳过创建")
            return

        # 创建表
        FraudHunterModelHitRecord.metadata.create_all(bind=engine)
        FraudHunterModelAlertControlRecord.metadata.create_all(bind=engine)

        logger.info("✓ 模型执行跟踪表创建成功！")

        # 验证表创建
        with SessionLocal() as db:
            # 验证命中记录表
            hit_count = db.execute(text("SELECT COUNT(*) FROM fraudhunter_hit_record")).scalar()
            logger.info(f"✓ fraudhunter_hit_record 表验证成功，当前记录数: {hit_count}")

            # 验证告警管控记录表
            alert_count = db.execute(text("SELECT COUNT(*) FROM fraudhunter_alert_control_record")).scalar()
            logger.info(f"✓ fraudhunter_alert_control_record 表验证成功，当前记录数: {alert_count}")

    except Exception as e:
        logger.error(f"创建模型执行跟踪表失败: {e}", exc_info=True)
        raise


def show_table_structure():
    """显示表结构信息"""
    try:
        logger.info("=" * 60)
        logger.info("表结构信息:")
        logger.info("=" * 60)

        with SessionLocal() as db:
            # 显示命中记录表结构
            logger.info("fraudhunter_hit_record 表结构:")
            try:
                result = db.execute(text("DESCRIBE fraudhunter_hit_record"))
                for row in result:
                    logger.info(f"  {row}")
            except Exception:
                # SQLite使用不同的命令
                result = db.execute(text("PRAGMA table_info(fraudhunter_hit_record)"))
                for row in result:
                    logger.info(f"  {row}")

            logger.info("-" * 40)

            # 显示告警管控记录表结构
            logger.info("fraudhunter_alert_control_record 表结构:")
            try:
                result = db.execute(text("DESCRIBE fraudhunter_alert_control_record"))
                for row in result:
                    logger.info(f"  {row}")
            except Exception:
                # SQLite使用不同的命令
                result = db.execute(text("PRAGMA table_info(fraudhunter_alert_control_record)"))
                for row in result:
                    logger.info(f"  {row}")

    except Exception as e:
        logger.warning(f"显示表结构失败: {e}")


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("模型执行跟踪系统数据库迁移")
    logger.info("=" * 60)

    try:
        create_model_execution_tracking_tables()
        show_table_structure()
        
        logger.info("=" * 60)
        logger.info("迁移成功完成！")
        logger.info("=" * 60)
    except Exception as e:
        logger.error("=" * 60)
        logger.error("迁移失败！")
        logger.error("=" * 60)
        sys.exit(1)