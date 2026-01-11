"""
实时数据清理定时任务

每日凌晨清理过期的实时数据
"""

from datetime import date, timedelta

from sqlalchemy import and_

from models.db_base import get_db_session
from models.fraudhunter.wide_table import FraudHunterWideTableSnapshot
from utils.logger import logger
from utils.config import settings
from utils.analyze_db_utils import AnalyzeDBPartitionManager

# 实时宽表名称
REALTIME_WIDE_TABLE = 'dep_acct_wide_table_realtime'
# 实时交易表名称
REALTIME_TRANSACTION_TABLE = 'realtime_oss_inct_new'


async def realtime_data_cleanup_job() -> None:
    """每日凌晨清理过期的实时数据"""
    if not settings.fraudhunter_realtime_data_enabled:
        logger.info("实时数据服务未启用，跳过清理任务")
        return

    try:
        retention_days = settings.fraudhunter_realtime_data_retention_days

        # 清理实时交易表的旧分区
        deleted_transaction_partitions = AnalyzeDBPartitionManager.cleanup_old_partitions(
            REALTIME_TRANSACTION_TABLE, retention_days
        )

        # 清理实时宽表快照记录
        deleted_snapshot_count = _cleanup_expired_snapshots(retention_days)

        logger.info(
            f"实时数据清理完成: "
            f"删除 {deleted_transaction_partitions} 个交易表分区, "
            f"删除 {deleted_snapshot_count} 条快照记录, "
            f"保留 {retention_days} 天数据"
        )

    except Exception as e:
        logger.error(f"清理实时数据失败: {e}", exc_info=True)


def _cleanup_expired_snapshots(retention_days: int) -> int:
    """清理过期的实时宽表快照记录

    Args:
        retention_days: 保留天数

    Returns:
        删除的快照数量
    """
    cutoff_date = date.today() - timedelta(days=retention_days)

    with get_db_session() as db:
        expired_snapshots = db.query(FraudHunterWideTableSnapshot).filter(
            and_(
                FraudHunterWideTableSnapshot.wide_table_name == REALTIME_WIDE_TABLE,
                FraudHunterWideTableSnapshot.etl_date < cutoff_date
            )
        ).all()

        deleted_count = len(expired_snapshots)
        for snapshot in expired_snapshots:
            db.delete(snapshot)
        db.commit()

        return deleted_count
