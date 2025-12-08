"""
为现有 IndicatorTask 填充 object_type 字段

迁移策略：
1. 如果任务有关联指标，取第一个指标的 object_type
2. 如果没有关联指标，默认使用 'cust_no'

使用方法：
    python backend/scripts/migrate_indicator_task_object_type.py
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from models.db_base import SessionLocal
from models.fraudhunter.indicator import (
    FraudHunterIndicatorTask,
    FraudHunterIndicatorDefinition
)
from utils.logger import logger


def migrate_object_type():
    """迁移所有指标任务的 object_type 字段"""
    db: Session = SessionLocal()
    try:
        # 查询所有任务
        tasks = db.query(FraudHunterIndicatorTask).all()
        logger.info(f"找到 {len(tasks)} 个指标任务需要迁移")

        updated = 0
        skipped = 0

        for task in tasks:
            # 如果已有 object_type 且不为空，跳过
            if hasattr(task, 'object_type') and task.object_type:
                logger.debug(f"任务 {task.task_code} 已有 object_type: {task.object_type}, 跳过")
                skipped += 1
                continue

            # 从关联指标获取 object_type
            if task.indicators and len(task.indicators) > 0:
                object_type = task.indicators[0].object_type
                logger.info(
                    f"任务 {task.task_code} 从关联指标获取 object_type: {object_type}"
                )
            else:
                object_type = 'cust_no'
                logger.warning(
                    f"任务 {task.task_code} 无关联指标，使用默认 object_type: {object_type}"
                )

            task.object_type = object_type
            updated += 1

        # 提交更改
        db.commit()
        logger.info(f"迁移完成: 更新 {updated} 个任务, 跳过 {skipped} 个任务")

        # 验证迁移结果
        tasks_without_object_type = db.query(FraudHunterIndicatorTask).filter(
            (FraudHunterIndicatorTask.object_type == None) |
            (FraudHunterIndicatorTask.object_type == '')
        ).count()

        if tasks_without_object_type > 0:
            logger.error(f"仍有 {tasks_without_object_type} 个任务没有 object_type，请检查！")
        else:
            logger.info("✓ 所有任务都已成功设置 object_type")

    except Exception as e:
        logger.error(f"迁移失败: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("开始迁移指标任务 object_type 字段")
    logger.info("=" * 60)

    try:
        migrate_object_type()
        logger.info("=" * 60)
        logger.info("迁移成功完成！")
        logger.info("=" * 60)
    except Exception as e:
        logger.error("=" * 60)
        logger.error("迁移失败！")
        logger.error("=" * 60)
        sys.exit(1)
