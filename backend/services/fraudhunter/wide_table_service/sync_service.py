"""
宽表同步服务 - 完整实现版
"""

from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_
import pandas as pd

from models.fraudhunter.wide_table import (
    FraudHunterWideTableVersion,
    FraudHunterWideTableSnapshot,
    FraudHunterIndicatorRunProgress
)
from .version_manager import WideTableVersionManager
from utils.logger import logger
from utils.config import settings
from utils.spark_utils import spark_utils


class WideTableSyncService:
    """宽表同步服务"""

    def __init__(self, db: Session):
        self.db = db
        self.storage_path = Path(settings.fraudhunter_wide_table_storage_path)
        self.source_table = settings.fraudhunter_wide_table_source_table
        self.version_manager = WideTableVersionManager(db)

    def sync_wide_table(
        self,
        target_version: FraudHunterWideTableVersion,
        etl_date: date
    ) -> Optional[FraudHunterWideTableSnapshot]:
        """同步单个版本的单个日期宽表

        Args:
            target_version: 目标版本对象
            etl_date: ETL日期

        Returns:
            成功则返回Snapshot对象，失败或跳过则返回None
        """
        snapshot = None

        try:
            # 1. 检查版本是否就绪
            is_ready, missing_tasks = self.version_manager.check_target_version_ready(
                target_version, etl_date
            )

            if not is_ready:
                logger.warning(
                    f"版本 {target_version.version_hash[:16]}... 在 {etl_date} 未就绪，"
                    f"缺失 {len(missing_tasks)} 个任务"
                )
                return None

            # 2. 检查是否已存在该日期的Snapshot
            existing_snapshot = self.db.query(FraudHunterWideTableSnapshot).filter(
                and_(
                    FraudHunterWideTableSnapshot.wide_table_name == target_version.wide_table_name,
                    FraudHunterWideTableSnapshot.etl_date == etl_date,
                    FraudHunterWideTableSnapshot.version_hash == target_version.version_hash
                )
            ).first()

            if existing_snapshot and existing_snapshot.status == 'ready':
                logger.info(f"该日期 {etl_date} 的宽表已存在且状态为ready，跳过同步")
                return existing_snapshot

            # 3. 创建或更新Snapshot记录（status='generating'）
            if existing_snapshot:
                snapshot = existing_snapshot
                snapshot.status = 'generating'
                snapshot.error_message = None
            else:
                snapshot = FraudHunterWideTableSnapshot(
                    wide_table_name=target_version.wide_table_name,
                    etl_date=etl_date,
                    version_hash=target_version.version_hash,
                    parquet_file_path="",  # 稍后更新
                    status='generating'
                )
                self.db.add(snapshot)

            self.db.commit()
            self.db.refresh(snapshot)

            logger.info(
                f"开始同步宽表: {target_version.wide_table_name}, "
                f"version={target_version.version_hash[:16]}..., "
                f"etl_date={etl_date}"
            )

            # 4. 构建Spark SQL PIVOT查询
            sql = self._build_pivot_sql(target_version, etl_date)

            # 5. 生成输出文件路径
            output_path = self._generate_wide_table_path(
                target_version.wide_table_name,
                target_version.version_hash,
                etl_date
            )

            # 6. 执行Spark查询并保存为Parquet
            row_count, column_count, file_size = self._execute_spark_query_and_save(
                sql, output_path
            )

            # 7. 更新Snapshot记录（status='ready'）
            snapshot.status = 'ready'
            snapshot.parquet_file_path = str(output_path)
            snapshot.row_count = row_count
            snapshot.column_count = column_count
            snapshot.file_size_bytes = file_size
            snapshot.generation_time = datetime.utcnow()
            snapshot.error_message = None
            self.db.commit()

            logger.info(
                f"宽表同步成功: {output_path.name}, "
                f"{row_count}行, {column_count}列, {file_size}字节"
            )

            # 8. 删除同日期的旧版本文件
            self._delete_old_version_files(
                target_version.wide_table_name,
                etl_date,
                target_version.version_hash
            )

            return snapshot

        except Exception as e:
            logger.error(
                f"宽表同步失败: {target_version.wide_table_name}, "
                f"etl_date={etl_date}, error={e}",
                exc_info=True
            )

            # 更新Snapshot为failed状态
            if snapshot:
                snapshot.status = 'failed'
                snapshot.error_message = str(e)[:1000]  # 限制长度
                self.db.commit()

            return None

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
        logger.info(
            f"开始批量同步宽表: {wide_table_name}, "
            f"回溯 {lookback_days} 天"
        )

        # 1. 获取target版本
        target_version = self.db.query(FraudHunterWideTableVersion).filter(
            and_(
                FraudHunterWideTableVersion.wide_table_name == wide_table_name,
                FraudHunterWideTableVersion.status == 'target'
            )
        ).first()

        if not target_version:
            logger.warning(f"{wide_table_name} 没有target版本，跳过同步")
            return {
                "wide_table_name": wide_table_name,
                "total_dates": 0,
                "synced": 0,
                "skipped": 0,
                "failed": 0,
                "details": []
            }

        # 2. 计算ETL日期范围 (今天往前lookback_days天)
        today = date.today()
        etl_dates = [today - timedelta(days=i) for i in range(lookback_days)]

        # 3. 遍历每个日期进行同步
        synced_count = 0
        skipped_count = 0
        failed_count = 0
        details = []

        for etl_date in etl_dates:
            try:
                snapshot = self.sync_wide_table(target_version, etl_date)

                if snapshot:
                    if snapshot.status == 'ready':
                        synced_count += 1
                        details.append({
                            "etl_date": str(etl_date),
                            "status": "synced",
                            "row_count": snapshot.row_count
                        })
                    elif snapshot.status == 'failed':
                        failed_count += 1
                        details.append({
                            "etl_date": str(etl_date),
                            "status": "failed",
                            "error": snapshot.error_message
                        })
                else:
                    skipped_count += 1
                    details.append({
                        "etl_date": str(etl_date),
                        "status": "skipped",
                        "reason": "version_not_ready"
                    })

            except Exception as e:
                failed_count += 1
                details.append({
                    "etl_date": str(etl_date),
                    "status": "failed",
                    "error": str(e)
                })
                logger.error(f"同步日期 {etl_date} 失败: {e}", exc_info=True)

        result = {
            "wide_table_name": wide_table_name,
            "total_dates": len(etl_dates),
            "synced": synced_count,
            "skipped": skipped_count,
            "failed": failed_count,
            "details": details
        }

        logger.info(
            f"{wide_table_name} 批量同步完成: "
            f"总计{len(etl_dates)}天, 成功{synced_count}, "
            f"跳过{skipped_count}, 失败{failed_count}"
        )

        return result

    def _build_pivot_sql(
        self,
        target_version: FraudHunterWideTableVersion,
        etl_date: date
    ) -> str:
        """构建Spark SQL PIVOT查询

        Args:
            target_version: 目标版本对象
            etl_date: ETL日期

        Returns:
            Spark SQL语句
        """
        # 1. 提取指标编码列表
        indicator_metadata = target_version.indicator_metadata
        indicator_codes = [
            meta['indicator_code']
            for meta in indicator_metadata.values()
        ]

        if not indicator_codes:
            raise ValueError("指标编码列表为空")

        # 2. 推断object_type
        object_type = self._get_object_type_from_wide_table_name(
            target_version.wide_table_name
        )

        # 3. 构建IN子句: 'ind_001' AS ind_001, 'ind_002' AS ind_002
        in_clause = ", ".join([f"'{code}' AS {code}" for code in indicator_codes])

        # 4. 构建SELECT列列表
        select_columns = ", ".join(indicator_codes)

        # 5. 构建完整SQL
        etl_date_str = etl_date.strftime('%Y-%m-%d')

        sql = f"""
SELECT
    target_id,
    {select_columns}
FROM (
    SELECT
        target_id,
        indicator_id,
        indicator_value
    FROM {self.source_table}
    WHERE etl_date = '{etl_date_str}'
      AND object_type = '{object_type}'
) AS source_data
PIVOT (
    MAX(indicator_value)
    FOR indicator_id IN ({in_clause})
)
""".strip()

        logger.debug(f"生成PIVOT SQL ({len(indicator_codes)}个指标):\n{sql}")
        return sql

    def _execute_spark_query_and_save(
        self,
        sql: str,
        output_path: Path
    ) -> Tuple[int, int, int]:
        """执行Spark SQL并保存为Parquet

        Args:
            sql: Spark SQL查询语句
            output_path: 输出文件路径

        Returns:
            (row_count, column_count, file_size_bytes)
        """
        logger.info(f"执行Spark查询并保存到: {output_path}")

        # 1. 执行Spark查询
        results = spark_utils.query_sql(sql, return_type='dict')

        if not results:
            logger.warning("Spark查询返回空结果")
            # 创建空DataFrame
            df = pd.DataFrame()
        else:
            # 2. 转换为DataFrame
            df = pd.DataFrame(results)

        # 3. 确保目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 4. 保存为Parquet
        df.to_parquet(output_path, engine='pyarrow', index=False)

        # 5. 获取统计信息
        row_count = len(df)
        column_count = len(df.columns)
        file_size = output_path.stat().st_size

        logger.info(
            f"Parquet文件已保存: {output_path.name}, "
            f"{row_count}行, {column_count}列, {file_size}字节"
        )

        return (row_count, column_count, file_size)

    def _generate_wide_table_path(
        self,
        wide_table_name: str,
        version_hash: str,
        etl_date: date
    ) -> Path:
        """生成宽表文件路径

        Args:
            wide_table_name: 宽表名称
            version_hash: 版本号
            etl_date: ETL日期

        Returns:
            文件路径
        """
        etl_date_str = etl_date.strftime('%Y%m%d')
        filename = f"{wide_table_name}_{version_hash}_{etl_date_str}.parquet"

        # 存储在子目录: {storage_path}/{wide_table_name}/
        table_dir = self.storage_path / wide_table_name
        return table_dir / filename

    def _delete_old_version_files(
        self,
        wide_table_name: str,
        etl_date: date,
        current_version_hash: str
    ):
        """删除同日期的旧版本文件

        Args:
            wide_table_name: 宽表名称
            etl_date: ETL日期
            current_version_hash: 当前版本号（保留）
        """
        table_dir = self.storage_path / wide_table_name
        if not table_dir.exists():
            return

        etl_date_str = etl_date.strftime('%Y%m%d')
        pattern = f"{wide_table_name}_*_{etl_date_str}.parquet"

        deleted_count = 0
        for file_path in table_dir.glob(pattern):
            # 检查是否是当前版本
            if current_version_hash not in file_path.name:
                try:
                    file_path.unlink()
                    deleted_count += 1
                    logger.info(f"删除旧版本文件: {file_path.name}")
                except Exception as e:
                    logger.error(f"删除文件失败 {file_path}: {e}")

        if deleted_count > 0:
            logger.info(f"清理完成，删除 {deleted_count} 个旧版本文件")

    def _get_object_type_from_wide_table_name(self, wide_table_name: str) -> str:
        """从宽表名称推断object_type

        Args:
            wide_table_name: 宽表名称

        Returns:
            object_type
        """
        # 反向映射
        reverse_mapping = {
            'dep_acct_wide_table': 'dep_acct_no',
            'cust_wide_table': 'cust_no',
            'loan_acct_wide_table': 'loan_acct_no',
        }

        object_type = reverse_mapping.get(wide_table_name)
        if not object_type:
            raise ValueError(f"未知的宽表名称: {wide_table_name}")

        return object_type
