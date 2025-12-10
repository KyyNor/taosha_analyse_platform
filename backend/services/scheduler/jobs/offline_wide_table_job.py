"""
离线指标宽表定时同步任务
从原 offline_scheduler.py 迁移而来

特点：
- 使用 asyncio.to_thread 在线程池中执行同步操作，不阻塞其他异步任务
- WideTableSyncService 不再持有长期的数据库连接，每次操作独立获取session
- sync_multi_dates 内部已包含版本切换逻辑，无需额外调用
"""

import asyncio
from typing import Dict
from utils.logger import logger


def _sync_wide_table(wide_table_name: str, lookback_days: int) -> Dict:
    """
    同步单个宽表（同步函数，在线程池中执行）
    
    注意：sync_multi_dates 内部已包含版本切换检查逻辑，
    当 target 快照数量 >= current 快照数量 * 0.5 时会自动提升版本

    Args:
        wide_table_name: 宽表名称
        lookback_days: 回溯天数

    Returns:
        同步结果字典，包含：
        - wide_table_name: 宽表名称
        - total_dates: 总日期数
        - synced: 成功同步数
        - skipped: 跳过数
        - failed: 失败数
        - version_promoted: 是否提升了版本
        - new_current_version: 新的current版本hash（如果提升了）
    """
    from services.fraudhunter.wide_table_service.sync_service import WideTableSyncService

    try:
        logger.info(f"[线程] 开始同步宽表: {wide_table_name}")

        # 创建服务实例（不需要传入db session）
        sync_service = WideTableSyncService()

        # 执行同步（内部已包含版本切换逻辑）
        result = sync_service.sync_multi_dates(
            wide_table_name=wide_table_name,
            lookback_days=lookback_days
        )

        # 日志输出
        log_msg = (
            f"[线程] {wide_table_name} 同步完成: "
            f"成功{result['synced']}, "
            f"跳过{result['skipped']}, "
            f"失败{result['failed']}"
        )
        
        # 如果版本被提升，追加日志
        if result.get('version_promoted'):
            log_msg += f", 版本已切换: {result.get('new_current_version')}"
        
        logger.info(log_msg)

        return result

    except Exception as e:
        logger.error(
            f"[线程] {wide_table_name} 同步失败: {e}",
            exc_info=True
        )
        return {
            "wide_table_name": wide_table_name,
            "total_dates": 0,
            "synced": 0,
            "skipped": 0,
            "failed": 1,
            "error": str(e),
            "version_promoted": False
        }


async def sync_all_wide_tables_job():
    """
    定时同步所有离线宽表（异步版本，不阻塞其他任务）

    遍历所有宽表（dep_acct_wide_table, cust_wide_table, loan_acct_wide_table）
    并调用同步服务进行批量同步

    特点：
    - 使用 asyncio.to_thread 将同步阻塞操作放到线程池执行
    - 不阻塞事件循环，允许其他异步任务正常运行
    - 各宽表的同步可以并行执行（可选）
    - sync_multi_dates 内部已包含版本切换逻辑，无需额外调用

    注意: 此函数由全局调度器调用，无需额外的文件锁
    启动锁机制已确保单进程执行
    """
    try:
        from utils.config import settings

        logger.info("=== 开始执行离线宽表定时同步（异步模式） ===")

        # 从配置读取回溯天数
        lookback_days = settings.fraudhunter_wide_table_sync_lookback_days

        # 遍历所有宽表
        wide_table_names = [
            'dep_acct_wide_table',
            'cust_wide_table',
            'loan_acct_wide_table'
        ]

        total_synced = 0
        total_skipped = 0
        total_failed = 0
        promoted_versions = []

        # 顺序执行每个宽表的同步（在线程池中）
        # 注意：这里选择顺序执行而非并行，避免Spark资源竞争
        for wide_table_name in wide_table_names:
            try:
                # 使用 asyncio.to_thread 在线程池中执行同步操作
                # 这样不会阻塞事件循环
                # sync_multi_dates 内部已包含版本切换检查和执行
                result = await asyncio.to_thread(
                    _sync_wide_table,
                    wide_table_name,
                    lookback_days
                )

                total_synced += result.get('synced', 0)
                total_skipped += result.get('skipped', 0)
                total_failed += result.get('failed', 0)
                
                # 记录版本切换信息
                if result.get('version_promoted'):
                    promoted_versions.append({
                        'wide_table_name': wide_table_name,
                        'new_version': result.get('new_current_version')
                    })

            except Exception as e:
                logger.error(
                    f"{wide_table_name} 同步失败: {e}",
                    exc_info=True
                )
                total_failed += 1

        # 汇总日志
        summary_msg = (
            f"=== 离线宽表定时同步完成 === "
            f"总计: 成功{total_synced}, 跳过{total_skipped}, 失败{total_failed}"
        )
        
        if promoted_versions:
            summary_msg += f", 版本切换: {len(promoted_versions)}个"
            for pv in promoted_versions:
                logger.info(
                    f"  ✓ {pv['wide_table_name']} 版本已切换至 {pv['new_version']}"
                )
        
        logger.info(summary_msg)

    except Exception as e:
        logger.error(f"离线宽表同步调度异常: {e}", exc_info=True)

