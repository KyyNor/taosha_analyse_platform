"""
宽表同步服务

支持两种执行模式：
1. PySpark模式：直接提交Spark任务执行查询，通过JDBC写入PostgreSQL（推荐）
2. JDBC模式：通过HiveServer2 JDBC连接执行查询，fetch结果后批量写入PG

为避免长时间运行导致MySQL连接丢失，所有数据库操作都使用独立的session。
"""

from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import date, datetime, timedelta

import pandas as pd

from models.fraudhunter.wide_table import (
    FraudHunterWideTableVersion,
    FraudHunterWideTableSnapshot,
)
from models.db_base import get_db_session
from .version_manager import WideTableVersionManager
from utils.logger import logger
from utils.config import settings
from utils.analyze_db_utils import AnalyzeDBConnector, AnalyzeDBPartitionManager

# 宽表名称到对象类型的反向映射
WIDE_TABLE_TO_OBJECT_TYPE = {
    'dep_acct_wide_table': 'dep_acct_no',
    'cust_wide_table': 'cust_no',
    'loan_acct_wide_table': 'loan_acct_no',
}


class WideTableSyncService:
    """宽表同步服务

    此服务不持有长期的db session引用，而是在每次数据库操作时获取新的session，
    以避免长时间Spark任务导致MySQL连接丢失。
    """

    def __init__(self) -> None:
        """初始化同步服务"""
        self.source_table = settings.fraudhunter_wide_table_source_table
        self._use_pyspark = settings.pyspark_enabled
        self._batch_size = settings.fraudhunter_realtime_writer_batch_insert_size

        mode = "PySpark" if self._use_pyspark else "JDBC"
        logger.info(f"宽表同步服务使用{mode}模式")

    def sync_wide_table(
        self,
        target_version_id: int,
        wide_table_name: str,
        version_hash: str,
        indicator_metadata: dict,
        etl_date: date
    ) -> Optional[Dict]:
        """同步单个版本的单个日期宽表

        Args:
            target_version_id: 目标版本ID
            wide_table_name: 宽表名称
            version_hash: 版本哈希
            indicator_metadata: 指标元数据
            etl_date: ETL日期

        Returns:
            成功: {"status": "ready", "id": snapshot_id, ...}
            跳过: {"status": "skipped", "skip_reason": reason, ...}
            失败: None
        """
        snapshot_id = None

        try:
            # 1. 检查版本是否就绪
            if not self._check_version_ready(target_version_id, etl_date, version_hash):
                return {
                    "status": "skipped",
                    "skip_reason": "version_not_ready",
                    "wide_table_name": wide_table_name,
                    "etl_date": str(etl_date)
                }

            # 2. 检查是否已存在ready状态的快照
            existing_result = self._get_existing_snapshot(
                wide_table_name, etl_date, version_hash
            )
            if existing_result:
                return existing_result

            # 3. 创建或更新Snapshot记录为generating状态
            snapshot_id = self._create_generating_snapshot(
                wide_table_name, etl_date, version_hash
            )

            # 4. 执行数据同步
            pg_table_name = f"{wide_table_name}_{version_hash[:8]}"
            row_count, column_count = self._execute_data_sync(
                wide_table_name, indicator_metadata, etl_date, pg_table_name
            )

            # 5. 更新Snapshot为ready状态
            self._update_snapshot_ready(
                snapshot_id, pg_table_name, row_count, column_count
            )

            logger.info(f"宽表同步成功: {pg_table_name}, {row_count}行, {column_count}列")

            return {
                "id": snapshot_id,
                "status": "ready",
                "row_count": row_count,
                "column_count": column_count,
                "file_size": 0,
                "is_new_sync": True
            }

        except Exception as e:
            logger.error(f"宽表同步失败: {wide_table_name}, etl_date={etl_date}, error={e}", exc_info=True)
            self._update_snapshot_failed(snapshot_id, str(e))
            return None

    def _check_version_ready(
        self,
        target_version_id: int,
        etl_date: date,
        version_hash: str
    ) -> bool:
        """检查版本是否就绪"""
        with get_db_session() as db:
            version_manager = WideTableVersionManager(db)
            target_version = db.query(FraudHunterWideTableVersion).get(target_version_id)

            if not target_version:
                logger.error(f"未找到版本 ID={target_version_id}")
                return False

            is_ready, missing_tasks = version_manager.check_target_version_ready(
                target_version, etl_date
            )

            if not is_ready:
                logger.debug(
                    f"版本 {version_hash[:16]}... 在 {etl_date} 未就绪，"
                    f"缺失 {len(missing_tasks)} 个任务"
                )
                return False

            return True

    def _get_existing_snapshot(
        self,
        wide_table_name: str,
        etl_date: date,
        version_hash: str
    ) -> Optional[Dict]:
        """检查是否已存在ready状态的快照"""
        from sqlalchemy import and_

        with get_db_session() as db:
            existing_snapshot = db.query(FraudHunterWideTableSnapshot).filter(
                and_(
                    FraudHunterWideTableSnapshot.wide_table_name == wide_table_name,
                    FraudHunterWideTableSnapshot.etl_date == etl_date,
                    FraudHunterWideTableSnapshot.version_hash == version_hash,
                    FraudHunterWideTableSnapshot.status == 'ready'
                )
            ).first()

            if existing_snapshot:
                logger.debug(f"该日期 {etl_date} 的宽表已存在且状态为ready，跳过同步")
                return {
                    "id": existing_snapshot.id,
                    "status": "ready",
                    "row_count": existing_snapshot.row_count,
                    "is_new_sync": False
                }

            return None

    def _create_generating_snapshot(
        self,
        wide_table_name: str,
        etl_date: date,
        version_hash: str
    ) -> int:
        """创建或更新Snapshot记录为generating状态，返回snapshot_id"""
        from sqlalchemy import and_

        with get_db_session() as db:
            existing_snapshot = db.query(FraudHunterWideTableSnapshot).filter(
                and_(
                    FraudHunterWideTableSnapshot.wide_table_name == wide_table_name,
                    FraudHunterWideTableSnapshot.etl_date == etl_date,
                    FraudHunterWideTableSnapshot.version_hash == version_hash
                )
            ).first()

            if existing_snapshot:
                existing_snapshot.status = 'generating'
                existing_snapshot.error_message = None
                db.commit()
                return existing_snapshot.id
            else:
                new_snapshot = FraudHunterWideTableSnapshot(
                    wide_table_name=wide_table_name,
                    etl_date=etl_date,
                    version_hash=version_hash,
                    parquet_file_path="",
                    status='generating'
                )
                db.add(new_snapshot)
                db.commit()
                db.refresh(new_snapshot)
                return new_snapshot.id

    def _execute_data_sync(
        self,
        wide_table_name: str,
        indicator_metadata: dict,
        etl_date: date,
        pg_table_name: str
    ) -> Tuple[int, int]:
        """执行数据同步

        Returns:
            (row_count, column_count)
        """
        # 1. 构建Spark SQL PIVOT查询
        sql = self._build_pivot_sql(wide_table_name, indicator_metadata, etl_date)

        # 2. 确保PG表和分区存在
        AnalyzeDBPartitionManager.create_wide_table(
            pg_table_name, indicator_metadata
        )
        AnalyzeDBPartitionManager.ensure_partition(pg_table_name, etl_date)

        # 3. 执行Spark查询并写入PG
        refresh_sql = f"refresh table {self.source_table}"
        return self._execute_spark_query_and_write_pg(
            sql, pg_table_name, etl_date, refresh_sql=refresh_sql
        )

    def _update_snapshot_ready(
        self,
        snapshot_id: int,
        pg_table_name: str,
        row_count: int,
        column_count: int
    ) -> None:
        """更新Snapshot为ready状态"""
        with get_db_session() as db:
            snapshot = db.query(FraudHunterWideTableSnapshot).get(snapshot_id)
            if snapshot:
                snapshot.status = 'ready'
                snapshot.parquet_file_path = pg_table_name
                snapshot.row_count = row_count
                snapshot.column_count = column_count
                snapshot.file_size_bytes = 0
                snapshot.generation_time = datetime.now()
                snapshot.error_message = None
                db.commit()

    def _update_snapshot_failed(self, snapshot_id: Optional[int], error_message: str) -> None:
        """更新Snapshot为failed状态"""
        if not snapshot_id:
            return

        try:
            with get_db_session() as db:
                snapshot = db.query(FraudHunterWideTableSnapshot).get(snapshot_id)
                if snapshot:
                    snapshot.status = 'failed'
                    snapshot.error_message = error_message[:1000]
                    db.commit()
        except Exception as db_error:
            logger.error(f"更新Snapshot失败状态时出错: {db_error}")

    def sync_multi_dates(
        self,
        wide_table_name: str,
        lookback_days: int
    ) -> Dict:
        """批量同步多个日期的宽表

        Args:
            wide_table_name: 宽表名称
            lookback_days: 回溯天数

        Returns:
            同步结果统计: {
                "wide_table_name": str,
                "total_dates": int,
                "synced": int,
                "skipped": int,
                "failed": int,
                "details": [...]
            }
        """
        from sqlalchemy import and_

        logger.info(f"开始同步宽表: {wide_table_name}, 回溯 {lookback_days} 天")

        # 1. 获取版本信息
        version_info = self._get_sync_version_info(wide_table_name)
        if not version_info:
            return self._empty_sync_result(wide_table_name, lookback_days)

        # 2. 计算ETL日期范围
        etl_dates = self._calculate_etl_dates(lookback_days)

        # 3. 遍历每个日期进行同步
        stats = self._sync_dates(
            etl_dates, wide_table_name, version_info
        )

        # 4. 构建结果并检查版本切换
        result = {
            "wide_table_name": wide_table_name,
            "total_dates": len(etl_dates),
            "synced": stats['synced'],
            "skipped": stats['skipped'],
            "skipped_ready": stats['skipped_ready'],
            "skipped_not_ready": stats['skipped_not_ready'],
            "failed": stats['failed'],
            "details": stats['details'],
            "version_promoted": False,
            "new_current_version": None
        }

        self._log_sync_summary(wide_table_name, result)

        # 5. 检查并执行版本切换
        if stats['synced'] > 0:
            self._try_promote_version(wide_table_name, result)

        return result

    def _get_sync_version_info(self, wide_table_name: str) -> Optional[Dict]:
        """获取用于同步的版本信息"""
        from sqlalchemy import and_

        with get_db_session() as db:
            target_version = db.query(FraudHunterWideTableVersion).filter(
                and_(
                    FraudHunterWideTableVersion.wide_table_name == wide_table_name,
                    FraudHunterWideTableVersion.status == 'target'
                )
            ).first()

            current_version = db.query(FraudHunterWideTableVersion).filter(
                and_(
                    FraudHunterWideTableVersion.wide_table_name == wide_table_name,
                    FraudHunterWideTableVersion.status == 'current'
                )
            ).first()

            if not target_version and not current_version:
                logger.warning(f"{wide_table_name} 没有target和current版本，跳过同步")
                return None

            # 优先使用target版本，否则使用current版本
            version = target_version or current_version
            return {
                'target_version_id': version.id,
                'version_hash': version.version_hash,
                'indicator_metadata': version.indicator_metadata
            }

    def _empty_sync_result(self, wide_table_name: str, lookback_days: int) -> Dict:
        """返回空的同步结果"""
        return {
            "wide_table_name": wide_table_name,
            "total_dates": lookback_days,
            "synced": 0,
            "skipped": 0,
            "failed": 0,
            "details": []
        }

    def _calculate_etl_dates(self, lookback_days: int) -> List[date]:
        """计算ETL日期范围"""
        today = date.today()
        return [today - timedelta(days=i) for i in range(lookback_days)]

    def _sync_dates(
        self,
        etl_dates: List[date],
        wide_table_name: str,
        version_info: Dict
    ) -> Dict:
        """同步多个日期，返回统计信息"""
        synced = skipped = skipped_ready = skipped_not_ready = failed = 0
        details = []

        for etl_date in etl_dates:
            result = self._sync_single_date(
                etl_date, wide_table_name, version_info
            )

            status = result.get('status')
            if status == 'ready' and result.get('is_new_sync', False):
                synced += 1
                logger.info(f"宽表同步成功: {wide_table_name} {etl_date}, {result.get('row_count')}行")
                details.append({
                    "etl_date": str(etl_date),
                    "status": "synced",
                    "row_count": result.get('row_count')
                })
            elif status == 'ready':
                skipped_ready += 1
                skipped += 1
                details.append({
                    "etl_date": str(etl_date),
                    "status": "already_ready",
                    "row_count": result.get('row_count')
                })
            elif status == 'skipped':
                skipped += 1
                if result.get('skip_reason') == 'version_not_ready':
                    skipped_not_ready += 1
                else:
                    skipped_ready += 1
                details.append({
                    "etl_date": str(etl_date),
                    "status": "skipped",
                    "reason": result.get('skip_reason')
                })
            else:
                failed += 1
                details.append({
                    "etl_date": str(etl_date),
                    "status": "failed",
                    "error": result.get('error', 'No result returned')
                })

        return {
            'synced': synced,
            'skipped': skipped,
            'skipped_ready': skipped_ready,
            'skipped_not_ready': skipped_not_ready,
            'failed': failed,
            'details': details
        }

    def _sync_single_date(
        self,
        etl_date: date,
        wide_table_name: str,
        version_info: Dict
    ) -> Dict:
        """同步单个日期

        Returns:
            同步结果字典，失败时返回 {"status": "failed", ...}
        """
        try:
            return self.sync_wide_table(
                target_version_id=version_info['target_version_id'],
                wide_table_name=wide_table_name,
                version_hash=version_info['version_hash'],
                indicator_metadata=version_info['indicator_metadata'],
                etl_date=etl_date
            )
        except Exception as e:
            logger.error(f"同步日期 {etl_date} 失败: {e}", exc_info=True)
            return {"status": "failed", "error": str(e)}

    def _log_sync_summary(self, wide_table_name: str, result: Dict) -> None:
        """记录同步汇总日志"""
        summary_parts = [
            f"总计{result['total_dates']}天",
            f"成功{result['synced']}"
        ]

        if result['skipped'] > 0:
            skip_parts = []
            if result['skipped_ready'] > 0:
                skip_parts.append(f"已存在{result['skipped_ready']}")
            if result['skipped_not_ready'] > 0:
                skip_parts.append(f"指标不足{result['skipped_not_ready']}")
            summary_parts.append(f"跳过({','.join(skip_parts)}){result['skipped']}")

        if result['failed'] > 0:
            summary_parts.append(f"失败{result['failed']}")

        logger.info(f"{wide_table_name} 同步完成: " + ", ".join(summary_parts))

    def _try_promote_version(self, wide_table_name: str, result: Dict) -> None:
        """尝试提升版本"""
        try:
            with get_db_session() as db:
                version_manager = WideTableVersionManager(db)
                promoted_version = version_manager.check_and_promote_target(wide_table_name)

                if promoted_version:
                    result['version_promoted'] = True
                    result['new_current_version'] = promoted_version.version_hash[:8]
                    logger.info(
                        f"{wide_table_name} 版本已自动切换: "
                        f"{promoted_version.version_hash[:8]} 成为新的current版本"
                    )
        except Exception as e:
            logger.error(f"检查版本切换时出错: {e}", exc_info=True)
            result['version_promote_error'] = str(e)

    def _build_pivot_sql(
        self,
        wide_table_name: str,
        indicator_metadata: dict,
        etl_date: date
    ) -> str:
        """构建Spark SQL PIVOT查询

        Args:
            wide_table_name: 宽表名称
            indicator_metadata: 指标元数据
            etl_date: ETL日期

        Returns:
            Spark SQL语句
        """
        # 1. 提取指标编码列表
        indicator_codes = [
            meta['indicator_code']
            for meta in indicator_metadata.values()
        ]

        if not indicator_codes:
            raise ValueError("指标编码列表为空")

        # 2. 推断object_type
        object_type = WIDE_TABLE_TO_OBJECT_TYPE.get(wide_table_name)
        if not object_type:
            raise ValueError(f"未知的宽表名称: {wide_table_name}")

        # 3. 构建PIVOT IN子句和SELECT列
        in_clause = ", ".join([f"'{code}' AS {code}" for code in indicator_codes])
        select_columns = ", ".join(indicator_codes)
        etl_date_str = etl_date.strftime('%Y-%m-%d')

        sql = f"""
SELECT
    target_id,
    {select_columns},
    '{etl_date_str}' as etl_date
FROM (
    SELECT
        target_id,
        indicator_id,
        indicator_value
    FROM {self.source_table}
    WHERE etl_date = '{etl_date_str}'
      AND object_type = '{object_type}'
      AND target_id is not null
) AS source_data
PIVOT (
    MAX(indicator_value)
    FOR indicator_id IN ({in_clause})
)
""".strip()

        logger.debug(f"生成PIVOT SQL ({len(indicator_codes)}个指标):\n{sql}")
        return sql

    def _execute_spark_query_and_write_pg(
        self,
        sql: str,
        pg_table_name: str,
        etl_date: date,
        refresh_sql: str
    ) -> Tuple[int, int]:
        """执行Spark SQL并写入PostgreSQL

        支持两种模式：
        1. PySpark模式：直接提交Spark任务，通过JDBC写入PG
        2. JDBC模式：通过JDBC连接fetch数据，批量写入PG

        Returns:
            (row_count, column_count)
        """
        if self._use_pyspark:
            return self._execute_with_pyspark_to_pg(sql, pg_table_name)
        else:
            from utils.spark_utils import spark_utils
            spark_utils.query_sql(refresh_sql, return_type='dict')
            return self._execute_with_jdbc_to_pg(sql, pg_table_name, etl_date)

    def _execute_with_pyspark_to_pg(
        self,
        sql: str,
        pg_table_name: str
    ) -> Tuple[int, int]:
        """使用PySpark执行查询并写入PG

        Returns:
            (row_count, column_count)
        """
        from utils.spark_utils import PySparkService

        logger.info(f"使用PySpark执行查询并写入PG表: {pg_table_name}")

        pyspark_service = PySparkService()
        try:
            if not pyspark_service.is_initialized():
                pyspark_service.initialize()

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
        etl_date: date
    ) -> Tuple[int, int]:
        """使用JDBC执行查询并批量写入PG

        Returns:
            (row_count, column_count)
        """
        from utils.spark_utils import spark_utils

        logger.info(f"使用JDBC执行Spark查询并写入PG表: {pg_table_name}")

        results = spark_utils.query_sql(sql, return_type='dict')

        if not results:
            logger.warning("Spark查询返回空结果")
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
