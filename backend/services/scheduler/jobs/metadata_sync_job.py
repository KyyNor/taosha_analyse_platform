"""
元数据同步定时任务
从原 main.py 中迁移而来

特点：
- 使用 asyncio.to_thread 在线程池中执行同步操作，不阻塞其他异步任务
- 每次执行时独立获取数据库session
- 支持配置启用/禁用
"""

import asyncio
from typing import Dict
from utils.logger import logger


def _sync_metadata() -> Dict:
    """
    执行元数据同步（同步函数，在线程池中执行）

    Returns:
        同步结果字典
    """
    from models.db_base import get_db_session
    from services.metadata_service.metadata_sync_service import MetadataSyncService

    try:
        with get_db_session() as db:
            sync_service = MetadataSyncService(db)
            result = sync_service.sync_metadata()

            if result["success"]:
                stats = result.get("stats", {})
                logger.info(
                    f"元数据同步完成: "
                    f"表新增{stats.get('tables_added', 0)}, "
                    f"表删除{stats.get('tables_removed', 0)}, "
                    f"列新增{stats.get('columns_added', 0)}, "
                    f"列删除{stats.get('columns_removed', 0)}, "
                    f"列更新{stats.get('columns_updated', 0)}"
                )
            else:
                logger.error(f"元数据同步失败: {result.get('error', 'Unknown error')}")

            return result

    except Exception as e:
        logger.error(f"元数据同步异常: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


async def metadata_sync_job():
    """
    定时执行元数据同步（异步版本，不阻塞其他任务）

    特点：
    - 使用 asyncio.to_thread 将同步阻塞操作放到线程池执行
    - 不阻塞事件循环，允许其他异步任务正常运行
    - 自动检查配置是否启用，未启用则跳过

    注意: 此函数由全局调度器调用，启动锁机制已确保单进程执行
    """
    try:
        from utils.config import settings

        # 检查是否启用
        if not settings.metadata_sync_enabled:
            logger.debug("元数据同步功能已禁用，跳过定时任务")
            return

        logger.info("=== 开始执行元数据定时同步 ===")

        # 使用 asyncio.to_thread 在线程池中执行同步操作
        result = await asyncio.to_thread(_sync_metadata)

        if result["success"]:
            logger.info("=== 元数据定时同步完成 ===")
        else:
            logger.error(f"=== 元数据定时同步失败: {result.get('error', 'Unknown')} ===")

    except Exception as e:
        logger.error(f"元数据同步调度异常: {e}", exc_info=True)
