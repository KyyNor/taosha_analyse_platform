"""
PG 离线宽表存储实现

阶段2纯重构：方法体从 sync_service.py 原样迁入（逻辑一行不改），
对 AnalyzeDBPartitionManager 的调用改为经本类委托，行为与重构前完全等价。
"""

from datetime import date
from typing import Tuple

import pandas as pd

from utils.config import settings
from utils.logger import logger
from .base import WideTableStore


class PgWideTableStore(WideTableStore):
    """PostgreSQL 离线宽表存储（现状路径的收编）"""

    name = 'postgresql'
    supports_delta_insert_select = True

    def __init__(self) -> None:
        self._use_pyspark = settings.pyspark_enabled
        self._batch_size = settings.fraudhunter_realtime_writer_batch_insert_size

        mode = "PySpark" if self._use_pyspark else "JDBC"
        logger.info(f"PG宽表存储使用{mode}模式")

    def ensure_table(
        self,
        table_name: str,
        indicator_metadata: dict,
        etl_date: date,
    ) -> None:
        """确保 PG 宽表和分区存在"""
        from utils.analyze_db_utils import AnalyzeDBPartitionManager

        AnalyzeDBPartitionManager.create_wide_table(table_name, indicator_metadata)
        AnalyzeDBPartitionManager.ensure_partition(table_name, etl_date)

    def create_heap_table(
        self,
        table_name: str,
        indicator_metadata: dict,
        **kwargs,
    ) -> None:
        """创建轻量无分区辅助表"""
        from utils.analyze_db_utils import AnalyzeDBPartitionManager

        AnalyzeDBPartitionManager.create_heap_table(table_name, indicator_metadata)

    def drop_table(self, table_name: str) -> None:
        from utils.analyze_db_utils import AnalyzeDBPartitionManager

        AnalyzeDBPartitionManager.drop_table(table_name)

    def write_pivot(
        self,
        sql: str,
        table_name: str,
        etl_date: date,
        refresh_sql: str | None = None,
    ) -> Tuple[int, int]:
        """执行Spark SQL并写入PG

        支持两种模式：
        1. PySpark模式：直接提交Spark任务，通过JDBC写入PG
        2. JDBC模式：通过JDBC连接fetch数据，批量写入PG

        Returns:
            (row_count, column_count)
        """
        if self._use_pyspark:
            return self._execute_with_pyspark_to_pg(sql, table_name, refresh_sql)
        else:
            return self._execute_with_jdbc_to_pg(sql, table_name, etl_date, refresh_sql)

    def merge_delta_insert_select(
        self,
        dest_table: str,
        base_table: str,
        delta_table: str | None,
        target_metadata: dict,
        static_cols: list,
        inc_cols: list,
        etl_date: str,
    ) -> int:
        from utils.analyze_db_utils import AnalyzeDBPartitionManager

        return AnalyzeDBPartitionManager.insert_select_from_base_delta(
            dest_table=dest_table,
            base_table=base_table,
            delta_table=delta_table,
            target_metadata=target_metadata,
            static_cols=static_cols,
            inc_cols=inc_cols,
            etl_date=etl_date,
        )

    def snapshot_ref(self, table_name: str, etl_date: date) -> str:
        """PG 快照引用即表名（现状语义不变）"""
        return table_name

    def _execute_with_pyspark_to_pg(
        self,
        sql: str,
        pg_table_name: str,
        refresh_sql: str | None = None,
    ) -> Tuple[int, int]:
        """使用PySpark执行查询并写入PG

        通用写入方法，同时服务于全量路径和增量路径（写辅助表），
        由调用方通过 pg_table_name 区分写入目标。

        Returns:
            (row_count, column_count)
        """
        from utils.spark_utils import PySparkService

        logger.info(f"使用PySpark执行查询并写入PG表: {pg_table_name}")

        pyspark_service = PySparkService()
        try:
            if not pyspark_service.is_initialized():
                pyspark_service.initialize()

            # refresh_sql 使源分区为最新内容（全量和增量路径均需要）
            if refresh_sql:
                pyspark_service.spark.sql(refresh_sql)

            df = pyspark_service.spark.sql(sql)
            column_count = len(df.columns)
            row_count = df.count()

            pg_config = settings.fraudhunter_analyze_db['postgresql']
            jdbc_url = (
                f"jdbc:postgresql://{pg_config['host']}:"
                f"{pg_config['port']}/{pg_config['database']}"
            )

            logger.info(f"开始写入PG表: {pg_table_name}, 预计{row_count}行")
            df.write.mode("append").option("driver", "org.postgresql.Driver").jdbc(
                url=jdbc_url,
                table=pg_table_name,
                properties={
                    "user": pg_config['user'],
                    "password": pg_config['password']
                }
            )

            return (row_count, column_count)
        finally:
            pyspark_service.shutdown()

    def _execute_with_jdbc_to_pg(
        self,
        sql: str,
        pg_table_name: str,
        etl_date: date,
        refresh_sql: str | None = None,
    ) -> Tuple[int, int]:
        """使用JDBC执行查询并批量写入PG

        通用写入方法，同时服务于全量路径和增量路径（写辅助表），
        由调用方通过 pg_table_name 区分写入目标。
        """

        from utils.analyze_db_utils import AnalyzeDBConnector
        from utils.spark_utils import spark_utils

        logger.info(f"使用JDBC执行Spark查询并写入PG表: {pg_table_name}")

        # refresh_sql 使源分区为最新内容（全量和增量路径均需要）
        if refresh_sql:
            spark_utils.query_sql(refresh_sql, return_type=None)

        results = spark_utils.query_sql(sql, return_type='dict')

        if not results:
            logger.warning(f"Spark查询返回空结果: {pg_table_name}")
            return (0, 0)

        df = pd.DataFrame(results)

        if 'etl_date' not in df.columns:
            df['etl_date'] = etl_date

        row_count = AnalyzeDBConnector.batch_insert(
            pg_table_name, df, chunksize=self._batch_size, if_exists='append'
        )
        column_count = len(df.columns)

        logger.info(f"数据已写入PG: {pg_table_name}, {row_count}行, {column_count}列")

        return (row_count, column_count)
