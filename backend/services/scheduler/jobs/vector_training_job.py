"""
向量数据库训练定时任务
从原 main.py 中迁移而来

特点：
- 使用 asyncio.to_thread 在线程池中执行同步操作，不阻塞其他异步任务
- 增量训练机制，只训练有变化的资源
- 每次执行时独立获取数据库session
"""

import asyncio
from typing import Dict
from utils.logger import logger


def _train_vector_database() -> Dict:
    """
    执行向量数据库训练（同步函数，在线程池中执行）

    Returns:
        训练结果字典
    """
    from models.db_base import get_db_session
    from services.vector_store.vector_training_service import VectorTrainingService

    try:
        with get_db_session() as db:
            training_service = VectorTrainingService(db)
            result = training_service.train_vector_database("定时任务的向量数据库训练")

            if result["success"]:
                trained_count = result.get("trained_count", 0)
                training_time = result.get("training_time", 0)

                if trained_count > 0:
                    logger.info(
                        f"向量数据库训练完成: "
                        f"训练了{trained_count}个资源, "
                        f"耗时{training_time:.2f}秒"
                    )
                else:
                    logger.debug("向量数据库训练完成: 没有需要训练的资源")
            else:
                logger.error(f"向量数据库训练失败: {result.get('error', 'Unknown error')}")

            return result

    except Exception as e:
        logger.error(f"向量数据库训练异常: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "trained_count": 0,
            "failed_count": 0
        }


async def vector_training_job():
    """
    定时执行向量数据库训练（异步版本，不阻塞其他任务）

    特点：
    - 使用 asyncio.to_thread 将同步阻塞操作放到线程池执行
    - 不阻塞事件循环，允许其他异步任务正常运行
    - 增量训练机制，只训练有变化的资源，避免全量训练的性能开销

    注意: 此函数由全局调度器调用，启动锁机制已确保单进程执行
    """
    try:
        logger.info("=== 开始执行向量数据库定时训练 ===")

        # 使用 asyncio.to_thread 在线程池中执行同步操作
        result = await asyncio.to_thread(_train_vector_database)

        if result["success"]:
            trained_count = result.get("trained_count", 0)
            if trained_count > 0:
                logger.info(f"=== 向量数据库定时训练完成: 训练了{trained_count}个资源 ===")
            else:
                logger.info("=== 向量数据库定时训练完成: 没有需要训练的资源 ===")
        else:
            logger.error(f"=== 向量数据库定时训练失败: {result.get('error', 'Unknown')} ===")

    except Exception as e:
        logger.error(f"向量数据库训练调度异常: {e}", exc_info=True)


def main():
    import asyncio
    from datetime import datetime
    logger.info(f"[{datetime.now()}] 向量数据库训练任务开始")
    asyncio.run(vector_training_job())
    logger.info(f"[{datetime.now()}] 向量数据库训练任务结束")

if __name__ == '__main__':
    main()
