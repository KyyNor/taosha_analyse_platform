"""
PostgreSQL数据清理定时任务

清理策略:
1. 实时交易明细表旧分区 (realtime_oss_inct_new)
2. 实时宽表旧分区 (dep_acct_wide_table_realtime_v*)
3. 离线宽表历史版本表 (非current/target状态的版本)
4. 孤立的快照记录 (对应PG表已不存在)
"""

from datetime import date, datetime, timedelta

from models.db_base import get_db_session
from models.fraudhunter.wide_table import FraudHunterWideTableVersion
from utils.logger import logger
from utils.config import settings
from utils.analyze_db_utils import AnalyzeDBPartitionManager


async def postgres_data_cleanup_job():
    """PostgreSQL数据清理任务

    包含四种清理策略：
    1. 实时交易明细表分区：按时间保留（默认7天）
    2. 实时宽表分区：按时间保留（默认21天）
    3. 离线宽表历史版本表：删除非current/target且超过30天的版本表
    4. 孤立的快照记录：标记为deleted
    """
    try:
        # 1. 清理实时交易明细表旧分区
        await _cleanup_realtime_transaction_partitions()

        # 2. 清理实时宽表旧分区
        await _cleanup_realtime_wide_table_partitions()

        # 3. 清理离线宽表历史版本表
        await _cleanup_history_wide_table_versions()

        # 4. 清理孤立的快照记录
        await _cleanup_orphaned_snapshot_records()

        await _ensure_realtime_partition()

        logger.info("PostgreSQL数据清理任务完成")

    except Exception as e:
        logger.error(f"PostgreSQL数据清理失败: {e}", exc_info=True)


async def _cleanup_realtime_transaction_partitions():
    """清理实时交易明细表旧分区

    清理策略：保留指定天数内的分区，删除过期分区
    """
    try:
        transaction_table = 'realtime_oss_inct_new'
        retention_days = settings.fraudhunter_realtime_data_retention_days

        logger.info(f"开始清理实时交易表分区，表={transaction_table}, 保留天数={retention_days}")

        deleted_count = AnalyzeDBPartitionManager.cleanup_old_partitions(
            transaction_table,
            retention_days
        )

        if deleted_count > 0:
            logger.info(f"实时交易表分区清理完成: 删除 {deleted_count} 个分区")
        else:
            logger.debug("没有需要清理的实时交易表分区")

    except Exception as e:
        logger.error(f"清理实时交易表分区失败: {e}", exc_info=True)


async def _cleanup_realtime_wide_table_partitions():
    """清理实时宽表旧分区

    清理策略：保留指定天数内的分区，删除过期分区
    同时清理非当前版本的实时宽表（先删分区，再删表）
    """
    try:
        retention_days = settings.fraudhunter_realtime_data_retention_days

        logger.info(f"开始清理实时宽表旧分区，保留天数={retention_days}")

        with get_db_session() as db:
            # 获取所有current版本的宽表
            current_versions = db.query(FraudHunterWideTableVersion).filter(
                FraudHunterWideTableVersion.status == 'current'
            ).all()

            if not current_versions:
                logger.debug("没有找到current版本的宽表，跳过清理实时宽表分区")
                return

            # 收集当前有效的实时宽表名
            current_realtime_tables = set()
            for version in current_versions:
                realtime_table_name = f"{version.wide_table_name}_realtime_{version.version_hash[:8]}"
                current_realtime_tables.add(realtime_table_name)

                # 清理该实时宽表的旧分区
                deleted_count = AnalyzeDBPartitionManager.cleanup_old_partitions(
                    realtime_table_name,
                    retention_days
                )

                logger.debug(f"当前实时宽表 {realtime_table_name}: 删除 {deleted_count} 个过期分区")

            logger.info(f"实时宽表分区清理完成，共 {len(current_realtime_tables)} 个当前版本表")

            # 清理非当前版本的实时宽表
            await _cleanup_non_current_realtime_tables(current_realtime_tables)

    except Exception as e:
        logger.error(f"清理实时宽表分区失败: {e}", exc_info=True)


async def _cleanup_non_current_realtime_tables(current_realtime_tables: set):
    """清理非当前版本的实时宽表

    策略：
    1. 查询所有包含 _realtime_ 的表
    2. 排除当前版本使用的实时宽表
    3. 对剩余的表：先清理所有分区，分区清零后删除整张表
    """
    try:
        logger.info("开始清理非当前版本的实时宽表...")

        # 获取当前数据库中所有以 _realtime_ 开头的表
        all_realtime_tables = AnalyzeDBPartitionManager.list_realtime_tables()

        # 过滤出非当前版本的表
        non_current_tables = [
            tbl for tbl in all_realtime_tables
            if tbl not in current_realtime_tables
        ]

        if not non_current_tables:
            logger.debug("没有发现非当前版本的实时宽表")
            return

        logger.info(f"发现 {len(non_current_tables)} 个非当前版本的实时宽表: {non_current_tables}")

        dropped_tables = 0
        failed_tables = []

        for table_name in non_current_tables:
            # 第一步：清理该表的所有分区
            deleted_count = AnalyzeDBPartitionManager.cleanup_old_partitions(
                table_name,
                retention_days=0  # 0表示删除所有分区
            )

            # 第二步：检查是否还有分区残留
            remaining_partitions = AnalyzeDBPartitionManager.list_partitions(table_name)

            if not remaining_partitions:
                # 分区已全部清理，可以删除主表
                if AnalyzeDBPartitionManager.drop_table(table_name):
                    dropped_tables += 1
                    logger.info(f"已删除非当前版本实时宽表: {table_name}")
                else:
                    failed_tables.append(table_name)
                    logger.warning(f"删除非当前版本实时宽表失败: {table_name}")
            else:
                # 还有分区残留，记录并跳过
                logger.warning(
                    f"非当前版本表 {table_name} 仍有 {len(remaining_partitions)} 个分区残留，暂不删除"
                )
                failed_tables.append(table_name)

        if dropped_tables > 0:
            logger.info(f"非当前版本实时宽表清理完成: 删除 {dropped_tables} 张表")
        if failed_tables:
            logger.warning(f"未能完全清理的非当前版本表: {failed_tables}")

    except Exception as e:
        logger.error(f"清理非当前版本实时宽表失败: {e}", exc_info=True)


async def _cleanup_history_wide_table_versions():
    """清理离线宽表历史版本表

    清理策略：
    1. 查找所有status='history'的版本记录
    2. 检查history_at时间是否超过30天
    3. 删除超过30天的版本对应的PG表和版本记录
    """
    try:
        history_retention_days = 30  # 历史版本保留30天

        logger.info(f"开始清理离线宽表历史版本表，保留天数={history_retention_days}")

        with get_db_session() as db:
            # 查询所有history状态的版本
            history_versions = db.query(FraudHunterWideTableVersion).filter(
                FraudHunterWideTableVersion.status == 'history'
            ).all()

            if not history_versions:
                logger.debug("没有找到history状态的宽表版本")
                return

            logger.info(f"找到 {len(history_versions)} 个history状态的版本")

            cutoff_date = date.today()
            deleted_tables = 0
            deleted_versions = 0

            for version in history_versions:
                # 检查版本是否超过保留期
                if version.history_at:
                    history_date = version.history_at.date()
                    days_since_history = (cutoff_date - history_date).days

                    if days_since_history > history_retention_days:
                        table_name = f"{version.wide_table_name}_{version.version_hash[:8]}"

                        logger.info(
                            f"删除历史版本表: {table_name}, "
                            f"history天数={days_since_history}, "
                            f"保留期={history_retention_days}天"
                        )

                        # 删除PG表
                        if AnalyzeDBPartitionManager.drop_table(table_name):
                            deleted_tables += 1
                            logger.debug(f"删除历史版本表成功: {table_name}")

                            # 删除版本记录
                            db.delete(version)
                            deleted_versions += 1
                        else:
                            logger.warning(f"删除历史版本表失败: {table_name}")

            if deleted_versions > 0:
                db.commit()
                logger.info(
                    f"历史版本表清理完成: 删除 {deleted_tables} 个表, "
                    f"删除 {deleted_versions} 条版本记录"
                )
            else:
                logger.debug("没有需要清理的历史版本表")

    except Exception as e:
        logger.error(f"清理历史版本表失败: {e}", exc_info=True)


async def _cleanup_orphaned_snapshot_records():
    """清理孤立的快照记录

    将对应PG表已不存在的快照记录状态标记为deleted
    """
    try:
        logger.info(f"开始清理孤立的快照记录")

        marked_count = AnalyzeDBPartitionManager.cleanup_orphaned_snapshots()

        if marked_count > 0:
            logger.info(f"孤立快照记录清理完成: 标记 {marked_count} 条记录为deleted")
        else:
            logger.debug("没有需要标记为deleted的孤立快照记录")

    except Exception as e:
        logger.error(f"清理孤立快照记录失败: {e}", exc_info=True)


async def _ensure_realtime_partition():
    logger.info(f"开始新建实时流水表分区")

    current_date = datetime.now()
    next_date_1 = (datetime.now() + timedelta(days=1))
    next_date_2 = (datetime.now() + timedelta(days=2))
    next_date_3 = (datetime.now() + timedelta(days=3))
    
    # 确保当前日期和后续3天分区存在
    AnalyzeDBPartitionManager.ensure_partition('realtime_oss_inct_new', current_date)
    AnalyzeDBPartitionManager.ensure_partition('realtime_oss_inct_new', next_date_1)
    AnalyzeDBPartitionManager.ensure_partition('realtime_oss_inct_new', next_date_2)
    AnalyzeDBPartitionManager.ensure_partition('realtime_oss_inct_new', next_date_3)


def main():
    import asyncio
    from datetime import datetime
    logger.info(f"[{datetime.now()}] PostgreSQL数据清理任务开始")
    asyncio.run(postgres_data_cleanup_job())
    logger.info(f"[{datetime.now()}] PostgreSQL数据清理任务结束")

if __name__ == '__main__':
    main()
