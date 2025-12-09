"""
宽表同步监控服务
"""

from typing import Optional
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_
from models.fraudhunter.wide_table import FraudHunterWideTableVersion
from services.fraudhunter.wide_table_service.version_manager import WideTableVersionManager
from services.fraudhunter.wide_table_service.sync_service import WideTableSyncService
from utils.logger import logger


class WideTableSyncMonitor:
    """宽表同步监控服务

    定期检查target版本是否可以同步，并触发同步任务
    """

    def __init__(self, db: Session):
        self.db = db
        self.version_manager = WideTableVersionManager(db)
        self.sync_service = WideTableSyncService(db)

    def check_and_sync_if_ready(
        self,
        wide_table_name: str,
        etl_date: Optional[date] = None
    ) -> Optional[FraudHunterWideTableVersion]:
        """检查并同步target版本(如果准备就绪)

        Args:
            wide_table_name: 宽表名称（dep_acct_wide_table/cust_wide_table/loan_acct_wide_table）
            etl_date: 要检查的ETL日期，默认为昨天

        Returns:
            如果成功同步，返回新的current版本；否则返回None
        """
        if etl_date is None:
            etl_date = date.today() - timedelta(days=1)

        # 1. 获取指定宽表的target版本
        target_version = self.db.query(FraudHunterWideTableVersion).filter(
            and_(
                FraudHunterWideTableVersion.wide_table_name == wide_table_name,
                FraudHunterWideTableVersion.status == 'target'
            )
        ).first()

        if not target_version:
            logger.debug(f"{wide_table_name}没有target版本，无需同步")
            return None

        # 2. 检查是否准备就绪
        is_ready, missing_tasks = self.version_manager.check_target_version_ready(
            target_version,
            etl_date
        )

        if not is_ready:
            logger.info(
                f"{wide_table_name}版本 {target_version.version_hash[:16]}... "
                f"在 {etl_date} 还未准备就绪，缺失 {len(missing_tasks)} 个任务"
            )
            return None

        # 3. 触发同步任务
        try:
            logger.info(
                f"开始同步{wide_table_name}版本 {target_version.version_hash[:16]}... "
                f"在 {etl_date} 的宽表"
            )

            snapshot = self.sync_service.sync_wide_table(
                target_version,
                etl_date
            )

            if snapshot and snapshot.status == 'ready':
                # 4. 提升版本状态
                current_version = self.version_manager.promote_target_to_current(target_version)
                logger.info(f"{wide_table_name}版本 {current_version.version_hash[:16]}... 已成功同步并提升为current")
                return current_version

            return None

        except Exception as e:
            logger.error(f"同步宽表时发生异常: {e}", exc_info=True)
            return None
