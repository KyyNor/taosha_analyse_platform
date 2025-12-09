"""
宽表同步监控服务

注意：此服务使用独立的数据库session进行操作，
避免长时间运行的Spark任务导致MySQL连接丢失
"""

from typing import Optional, Dict
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_
from models.fraudhunter.wide_table import FraudHunterWideTableVersion
from models.db_base import get_db_session
from services.fraudhunter.wide_table_service.version_manager import WideTableVersionManager
from services.fraudhunter.wide_table_service.sync_service import WideTableSyncService
from utils.logger import logger


class WideTableSyncMonitor:
    """宽表同步监控服务

    定期检查target版本是否可以同步，并触发同步任务
    
    注意：此服务不再持有长期的数据库session，
    而是在需要时获取独立的session进行操作
    """

    def __init__(self):
        """初始化监控服务（不持有db session）"""
        self.sync_service = WideTableSyncService()

    def check_and_sync_if_ready(
        self,
        wide_table_name: str,
        etl_date: Optional[date] = None
    ) -> Optional[Dict]:
        """检查并同步target版本(如果准备就绪)

        Args:
            wide_table_name: 宽表名称（dep_acct_wide_table/cust_wide_table/loan_acct_wide_table）
            etl_date: 要检查的ETL日期，默认为昨天

        Returns:
            如果成功同步，返回版本信息字典；否则返回None
        """
        if etl_date is None:
            etl_date = date.today() - timedelta(days=1)

        # 使用独立session获取target版本信息
        target_version_id = None
        version_hash = None
        indicator_metadata = None
        
        with get_db_session() as db:
            version_manager = WideTableVersionManager(db)
            
            # 1. 获取指定宽表的target版本
            target_version = db.query(FraudHunterWideTableVersion).filter(
                and_(
                    FraudHunterWideTableVersion.wide_table_name == wide_table_name,
                    FraudHunterWideTableVersion.status == 'target'
                )
            ).first()

            if not target_version:
                logger.debug(f"{wide_table_name}没有target版本，无需同步")
                return None

            # 2. 检查是否准备就绪
            is_ready, missing_tasks = version_manager.check_target_version_ready(
                target_version,
                etl_date
            )

            if not is_ready:
                logger.info(
                    f"{wide_table_name}版本 {target_version.version_hash[:16]}... "
                    f"在 {etl_date} 还未准备就绪，缺失 {len(missing_tasks)} 个任务"
                )
                return None
            
            # 提取需要的信息
            target_version_id = target_version.id
            version_hash = target_version.version_hash
            indicator_metadata = target_version.indicator_metadata

        # 3. 触发同步任务
        try:
            logger.info(
                f"开始同步{wide_table_name}版本 {version_hash[:16]}... "
                f"在 {etl_date} 的宽表"
            )

            # 调用新的sync_wide_table接口
            result = self.sync_service.sync_wide_table(
                target_version_id=target_version_id,
                wide_table_name=wide_table_name,
                version_hash=version_hash,
                indicator_metadata=indicator_metadata,
                etl_date=etl_date
            )

            if result and result.get('status') == 'ready':
                # 4. 使用独立session提升版本状态
                with get_db_session() as db:
                    version_manager = WideTableVersionManager(db)
                    target_version = db.query(FraudHunterWideTableVersion).get(target_version_id)
                    if target_version:
                        current_version = version_manager.promote_target_to_current(target_version)
                        logger.info(
                            f"{wide_table_name}版本 {current_version.version_hash[:16]}... "
                            f"已成功同步并提升为current"
                        )
                        return {
                            "version_id": current_version.id,
                            "version_hash": current_version.version_hash,
                            "status": current_version.status
                        }

            return None

        except Exception as e:
            logger.error(f"同步宽表时发生异常: {e}", exc_info=True)
            return None
