"""
实时数据清理定时任务
每日凌晨清理过期的实时数据
"""

from pathlib import Path

import duckdb

from utils.config import settings
from utils.logger import logger


async def cleanup_realtime_data():
    """每日凌晨清理过期的实时数据"""
    if not settings.fraudhunter_realtime_data_enabled:
        logger.info("实时数据服务未启用，跳过清理任务")
        return

    try:
        db_path = Path(settings.fraudhunter_realtime_data_storage_path) / "realtime_data.duckdb"

        if not db_path.exists():
            logger.warning(f"实时数据库文件不存在: {db_path}")
            return

        # 连接数据库
        conn = duckdb.connect(str(db_path))

        # 删除过期数据
        retention_days = settings.fraudhunter_realtime_data_retention_days
        result = conn.execute(f"""
            DELETE FROM realtime_oss_inct_new
            WHERE tran_date < CURRENT_DATE - INTERVAL '{retention_days} days'
        """)

        # 获取删除的行数
        deleted_rows = result.fetchone()
        deleted_count = deleted_rows[0] if deleted_rows else 0

        # VACUUM压缩文件
        conn.execute("VACUUM")

        # 关闭连接
        conn.close()

        logger.info(f"实时数据清理完成: 删除 {deleted_count} 行，保留 {retention_days} 天数据")

    except Exception as e:
        logger.error(f"清理实时数据失败: {e}", exc_info=True)
