"""
离线指标宽表定时同步任务
从原 offline_scheduler.py 迁移而来
"""

from models.db_base import get_db_session
from utils.logger import logger


async def sync_all_wide_tables_job():
    """
    定时同步所有离线宽表

    遍历所有宽表（dep_acct_wide_table, cust_wide_table, loan_acct_wide_table）
    并调用同步服务进行批量同步

    注意: 此函数由全局调度器调用，无需额外的文件锁
    启动锁机制已确保单进程执行
    """
    try:
        from services.fraudhunter.wide_table_service.sync_service import WideTableSyncService
        from utils.config import settings

        logger.info("=== 开始执行离线宽表定时同步 ===")

        # 从配置读取回溯天数
        lookback_days = settings.fraudhunter_wide_table_sync_lookback_days

        with get_db_session() as db:
            sync_service = WideTableSyncService(db)

            # 遍历所有宽表
            wide_table_names = [
                'dep_acct_wide_table',
                'cust_wide_table',
                'loan_acct_wide_table'
            ]

            total_synced = 0
            total_skipped = 0
            total_failed = 0

            for wide_table_name in wide_table_names:
                try:
                    logger.info(f"开始同步宽表: {wide_table_name}")

                    result = sync_service.sync_multi_dates(
                        wide_table_name=wide_table_name,
                        lookback_days=lookback_days
                    )

                    total_synced += result['synced']
                    total_skipped += result['skipped']
                    total_failed += result['failed']

                    logger.info(
                        f"{wide_table_name} 同步完成: "
                        f"成功{result['synced']}, "
                        f"跳过{result['skipped']}, "
                        f"失败{result['failed']}"
                    )

                except Exception as e:
                    logger.error(
                        f"{wide_table_name} 同步失败: {e}",
                        exc_info=True
                    )
                    total_failed += 1

            logger.info(
                f"=== 离线宽表定时同步完成 === "
                f"总计: 成功{total_synced}, 跳过{total_skipped}, 失败{total_failed}"
            )

    except Exception as e:
        logger.error(f"离线宽表同步调度异常: {e}", exc_info=True)
