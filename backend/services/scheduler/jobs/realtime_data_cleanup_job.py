"""
实时数据清理定时任务
每日凌晨清理过期的实时数据
"""

from datetime import date, timedelta

from models.db_base import get_db_session
from models.fraudhunter.wide_table import FraudHunterWideTableSnapshot
from sqlalchemy import and_
from utils.logger import logger
from utils.config import settings
from utils.analyze_db_utils import AnalyzeDBPartitionManager


async def realtime_data_cleanup_job():
    """每日凌晨清理过期的实时数据"""
    if not settings.fraudhunter_realtime_data_enabled:
        logger.info("实时数据服务未启用，跳过清理任务")
        return

    try:
        retention_days = settings.fraudhunter_realtime_data_retention_days

        # 清理实时交易表的旧分区
        deleted_transaction_partitions = AnalyzeDBPartitionManager.cleanup_old_partitions(
            'realtime_oss_inct_new', retention_days
        )

        # 清理实时宽表快照记录
        cutoff_date = date.today() - timedelta(days=retention_days)
        with get_db_session() as db:
            # 查询过期的快照记录
            expired_snapshots = db.query(FraudHunterWideTableSnapshot).filter(
                and_(
                    FraudHunterWideTableSnapshot.wide_table_name == 'dep_acct_wide_table_realtime',
                    FraudHunterWideTableSnapshot.etl_date < cutoff_date
                )
            ).all()

            # 删除快照记录
            deleted_snapshot_count = len(expired_snapshots)
            for snapshot in expired_snapshots:
                db.delete(snapshot)
            db.commit()

        logger.info(
            f"实时数据清理完成: "
            f"删除 {deleted_transaction_partitions} 个交易表分区, "
            f"删除 {deleted_snapshot_count} 条快照记录, "
            f"保留 {retention_days} 天数据"
        )

    except Exception as e:
        logger.error(f"清理实时数据失败: {e}", exc_info=True)
