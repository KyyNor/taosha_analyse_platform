"""
宽表同步服务 - 完整实现版

支持两种执行模式：
1. JDBC模式：通过HiveServer2 JDBC连接执行查询，fetch结果后本地保存
2. PySpark模式：直接提交Spark任务执行查询并输出文件（推荐用于大数据量）

注意：为避免长时间运行导致MySQL连接丢失，所有数据库操作都使用独立的session
"""

from pathlib import Path
from typing import List, Dict, Optional, Tuple, Callable, Union
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_
import pandas as pd
import requests
import pyarrow as pa
import pyarrow.parquet as pq
import shutil
from pathlib import Path
from tqdm import tqdm  # 显示进度条

from models.fraudhunter.wide_table import (
    FraudHunterWideTableVersion,
    FraudHunterWideTableSnapshot,
    FraudHunterIndicatorRunProgress
)
from models.db_base import get_db_session
from .version_manager import WideTableVersionManager
from utils.logger import logger
from utils.config import settings


class WideTableSyncService:
    """
    宽表同步服务
    
    注意：此服务不再持有长期的db session引用，
    而是在每次数据库操作时获取新的session，
    以避免长时间Spark任务导致MySQL连接丢失。
    """

    def __init__(self):
        """初始化同步服务（不再持有db session）"""
        self.storage_path = Path(settings.fraudhunter_wide_table_storage_path)
        self.source_table = settings.fraudhunter_wide_table_source_table
        self._use_pyspark = settings.pyspark_enabled
        
        if self._use_pyspark:
            logger.info("宽表同步服务使用PySpark模式")
        else:
            logger.info("宽表同步服务使用JDBC模式")

    def _get_version_manager(self) -> WideTableVersionManager:
        """获取一个新的VersionManager实例（使用独立session）"""
        # 注意：这里返回的是一个需要在with语句中使用的对象
        # 或者创建临时session
        pass  # 将在具体方法中直接创建session

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
            成功：返回包含snapshot信息的字典
            跳过：返回包含status='skipped'和skip_reason的字典
            失败：返回None（异常情况）
        """
        snapshot_id = None

        try:
            # 1. 使用独立session检查版本是否就绪
            with get_db_session() as db:
                version_manager = WideTableVersionManager(db)
                target_version = db.query(FraudHunterWideTableVersion).get(target_version_id)
                
                if not target_version:
                    logger.error(f"未找到版本 ID={target_version_id}")
                    return None
                
                is_ready, missing_tasks = version_manager.check_target_version_ready(
                    target_version, etl_date
                )

                if not is_ready:
                    logger.debug(
                        f"版本 {version_hash[:16]}... 在 {etl_date} 未就绪，"
                        f"缺失 {len(missing_tasks)} 个任务"
                    )
                    return {
                        "status": "skipped",
                        "skip_reason": "version_not_ready",
                        "wide_table_name": wide_table_name,
                        "etl_date": str(etl_date)
                    }

            # 2. 使用独立session检查是否已存在该日期的Snapshot
            with get_db_session() as db:
                existing_snapshot = db.query(FraudHunterWideTableSnapshot).filter(
                    and_(
                        FraudHunterWideTableSnapshot.wide_table_name == wide_table_name,
                        FraudHunterWideTableSnapshot.etl_date == etl_date,
                        FraudHunterWideTableSnapshot.version_hash == version_hash
                    )
                ).first()

                if existing_snapshot and existing_snapshot.status == 'ready':
                    logger.debug(f"该日期 {etl_date} 的宽表已存在且状态为ready，跳过同步")
                    # 添加is_new_sync标志，标识这不是新同步的
                    return {
                        "id": existing_snapshot.id,
                        "status": "ready",
                        "row_count": existing_snapshot.row_count,
                        "is_new_sync": False  # 标识这是已存在的，不是新同步的
                    }

                # 3. 创建或更新Snapshot记录（status='generating'）
                if existing_snapshot:
                    existing_snapshot.status = 'generating'
                    existing_snapshot.error_message = None
                    db.commit()
                    snapshot_id = existing_snapshot.id
                else:
                    new_snapshot = FraudHunterWideTableSnapshot(
                        wide_table_name=wide_table_name,
                        etl_date=etl_date,
                        version_hash=version_hash,
                        parquet_file_path="",  # 稍后更新
                        status='generating'
                    )
                    db.add(new_snapshot)
                    db.commit()
                    db.refresh(new_snapshot)
                    snapshot_id = new_snapshot.id

            # 开始同步日志由上层统一处理

            # 4. 构建Spark SQL PIVOT查询
            sql = self._build_pivot_sql(wide_table_name, indicator_metadata, etl_date)

            etl_date_str = etl_date.strftime('%Y%m%d')
            # 5. 生成输出文件路径
            output_path = self._generate_wide_table_path(
                wide_table_name,
                version_hash,
                etl_date_str
            )

            
            hdfs_filepath = f"{wide_table_name}_{etl_date_str}"

            # 6. 执行Spark查询并保存为Parquet（这是耗时操作）
            row_count, column_count, file_size = self._execute_spark_query_and_save(
                sql, output_path, hdfs_filepath, refresh_sql = f"refresh table {self.source_table}"
            )

            # 7. 使用独立session更新Snapshot记录（status='ready'）
            with get_db_session() as db:
                snapshot = db.query(FraudHunterWideTableSnapshot).get(snapshot_id)
                if snapshot:
                    snapshot.status = 'ready'
                    snapshot.parquet_file_path = str(output_path)
                    snapshot.row_count = row_count
                    snapshot.column_count = column_count
                    snapshot.file_size_bytes = file_size
                    snapshot.generation_time = datetime.now()
                    snapshot.error_message = None
                    db.commit()

            logger.info(
                f"宽表同步成功: {output_path.name}, "
                f"{row_count}行, {column_count}列, {file_size}字节"
            )


            return {
                "id": snapshot_id,
                "status": "ready",
                "row_count": row_count,
                "column_count": column_count,
                "file_size": file_size,
                "is_new_sync": True  # 标识这是新同步的
            }

        except Exception as e:
            logger.error(
                f"宽表同步失败: {wide_table_name}, "
                f"etl_date={etl_date}, error={e}",
                exc_info=True
            )

            # 使用独立session更新Snapshot为failed状态
            if snapshot_id:
                try:
                    with get_db_session() as db:
                        snapshot = db.query(FraudHunterWideTableSnapshot).get(snapshot_id)
                        if snapshot:
                            snapshot.status = 'failed'
                            snapshot.error_message = str(e)[:1000]  # 限制长度
                            db.commit()
                except Exception as db_error:
                    logger.error(f"更新Snapshot失败状态时出错: {db_error}")

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
        logger.info(f"开始同步宽表: {wide_table_name}, 回溯 {lookback_days} 天")

        # 1. 使用独立session获取target版本信息
        target_version_id = None
        version_hash = None
        indicator_metadata = None
        
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
                return {
                    "wide_table_name": wide_table_name,
                    "total_dates": 0,
                    "synced": 0,
                    "skipped": 0,
                    "failed": 0,
                    "details": []
                }
            
            # 提取需要的数据，避免session关闭后无法访问
            if target_version:
                target_version_id = target_version.id
                version_hash = target_version.version_hash
                indicator_metadata = target_version.indicator_metadata
            else:
                target_version_id = current_version.id
                version_hash = current_version.version_hash
                indicator_metadata = current_version.indicator_metadata

        # 2. 计算ETL日期范围 (今天往前lookback_days天)
        today = date.today()
        etl_dates = [today - timedelta(days=i) for i in range(lookback_days)]

        # 3. 遍历每个日期进行同步
        synced_count = 0
        skipped_count = 0
        skipped_ready_count = 0  # 因已存在ready状态而跳过的天数
        skipped_not_ready_count = 0  # 因版本未就绪而跳过的天数
        failed_count = 0
        details = []

        for etl_date in etl_dates:
            try:
                result = self.sync_wide_table(
                    target_version_id=target_version_id,
                    wide_table_name=wide_table_name,
                    version_hash=version_hash,
                    indicator_metadata=indicator_metadata,
                    etl_date=etl_date
                )

                if result:
                    status = result.get('status')

                    if status == 'ready':
                        if result.get('is_new_sync', False):
                            # 新同步的才计入成功统计并打印日志
                            synced_count += 1
                            logger.info(
                                f"宽表同步成功: {wide_table_name} {etl_date}, "
                                f"{result.get('row_count')}行"
                            )
                            details.append({
                                "etl_date": str(etl_date),
                                "status": "synced",
                                "row_count": result.get('row_count')
                            })
                        else:
                            # 已存在的计入跳过统计
                            skipped_ready_count += 1
                            skipped_count += 1
                            details.append({
                                "etl_date": str(etl_date),
                                "status": "already_ready",
                                "row_count": result.get('row_count')
                            })

                    elif status == 'skipped':
                        # 根据返回的跳过原因进行统计
                        skip_reason = result.get('skip_reason')
                        if skip_reason == 'version_not_ready':
                            skipped_not_ready_count += 1
                        else:
                            skipped_ready_count += 1

                        skipped_count += 1
                        details.append({
                            "etl_date": str(etl_date),
                            "status": "skipped",
                            "reason": skip_reason
                        })
                    else:
                        # 其他状态（如failed）
                        failed_count += 1
                        details.append({
                            "etl_date": str(etl_date),
                            "status": "failed",
                            "error": result.get('error', 'Unknown error')
                        })
                else:
                    # None返回值表示异常情况
                    failed_count += 1
                    details.append({
                        "etl_date": str(etl_date),
                        "status": "failed",
                        "error": "No result returned"
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
            "skipped_ready": skipped_ready_count,
            "skipped_not_ready": skipped_not_ready_count,
            "failed": failed_count,
            "details": details,
            "version_promoted": False,
            "new_current_version": None
        }

        # 构建详细的汇总信息
        summary_parts = [
            f"总计{len(etl_dates)}天",
            f"成功{synced_count}"
        ]

        # 如果有跳过的，显示跳过原因
        if skipped_count > 0:
            skip_parts = []
            if skipped_ready_count > 0:
                skip_parts.append(f"已存在{skipped_ready_count}")
            if skipped_not_ready_count > 0:
                skip_parts.append(f"指标不足{skipped_not_ready_count}")
            summary_parts.append(f"跳过({','.join(skip_parts)}){skipped_count}")

        # 如果有失败的，显示失败数
        if failed_count > 0:
            summary_parts.append(f"失败{failed_count}")

        logger.info(f"{wide_table_name} 同步完成: " + ", ".join(summary_parts))

        # 4. 检查并执行版本切换
        if synced_count > 0:
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

        return result

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
        object_type = self._get_object_type_from_wide_table_name(wide_table_name)

        # 3. 构建IN子句: 'ind_001' AS ind_001, 'ind_002' AS ind_002
        in_clause = ", ".join([f"'{code}' AS {code}" for code in indicator_codes])

        # 4. 构建SELECT列列表
        select_columns = ", ".join(indicator_codes)

        # 5. 构建完整SQL
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
        output_path: Path,
        hdfs_filepath: str,
        refresh_sql: str
    ) -> Tuple[int, int, int]:
        """执行Spark SQL并保存为Parquet

        支持两种模式：
        1. PySpark模式：直接提交Spark任务，高效处理大数据量
        2. JDBC模式：通过JDBC连接fetch数据，适合小数据量

        Args:
            sql: Spark SQL查询语句
            output_path: 输出文件路径

        Returns:
            (row_count, column_count, file_size_bytes)
        """
        if self._use_pyspark:
            from utils.spark_utils import PySparkService
            _pyspark_service = PySparkService()
            _pyspark_service.initialize()
            r = self._execute_with_pyspark(sql, output_path, hdfs_filepath, _pyspark_service)
            _pyspark_service.shutdown()
            return r
        else:
            from utils.spark_utils import spark_utils
            spark_utils.query_sql(refresh_sql, return_type='dict')
            return self._execute_with_jdbc(sql, output_path)
    
    def _execute_with_pyspark(
        self,
        sql: str,
        output_path: Path,
        hdfs_filepath: str,
        pyspark_service
    ) -> Tuple[int, int, int]:
        """使用PySpark执行查询并保存
        
        Args:
            sql: Spark SQL查询语句
            output_path: 输出文件路径

        Returns:
            (row_count, column_count, file_size_bytes)
        """
        logger.info(f"使用PySpark执行查询并保存到: {output_path}")
        
        # 确保PySpark已初始化
        if not pyspark_service.is_initialized():
            logger.info("PySpark未初始化，正在初始化...")
            if not pyspark_service.initialize():
                raise RuntimeError("PySpark初始化失败，无法执行查询")
        
        if pyspark_service.spark is None or pyspark_service.spark._sc._jsc is None:
            pyspark_service.initialize()

        # 执行SQL查询
        hdfs_file_path = f'/taosha/wide_tables/{hdfs_filepath}'

        df = pyspark_service.spark.sql(sql)
        df.write.mode("overwrite").parquet(hdfs_file_path)
        
        # 获取列数
        column_count = len(df.columns)
        row_count = df.count()
        
        # 构建临时目录
        tmp_output_path = output_path.parent / f'tmp_{hdfs_filepath}'

        if tmp_output_path.exists():
            logger.info(f'删除临时目录 ： {tmp_output_path}')
            shutil.rmtree(tmp_output_path)
        
        tmp_output_path.mkdir(parents=True, exist_ok=True)

        logger.info(f'开始从HDFS下载文件到本地临时目录 : {hdfs_file_path}  -->  {tmp_output_path}')
        self.download_hdfs_directory(hdfs_file_path, tmp_output_path)
        
        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f'将临时目录合并为最终文件 : {tmp_output_path}  -->  {output_path}')
        self.merge_parquet(tmp_output_path, output_path)

        logger.info(f'删除临时目录 ： {tmp_output_path}')
        shutil.rmtree(tmp_output_path)

        file_size = output_path.stat().st_size if output_path.exists() else 0

        return (row_count, column_count, file_size)

    def download_hdfs_directory(self, hdfs_dir: str, local_dir: Path):
        """递归下载HDFS目录到本地"""
        namenode_host = "bigdata01"
        webhdfs_port = "50070"
        
        # 1. 列出目录内容
        list_url = f"http://{namenode_host}:{webhdfs_port}/webhdfs/v1{hdfs_dir}"
        
        list_params = {"op": "LISTSTATUS"}
        
        try:
            response = requests.get(list_url, params=list_params)
            response.raise_for_status()
            files = response.json()['FileStatuses']['FileStatus']
            
            # 3. 遍历下载
            for item in tqdm(files, desc=f"Downloading {hdfs_dir}"):
                file_name = item['pathSuffix']
                hdfs_path = f"{hdfs_dir}/{file_name}"
                local_path = local_dir / file_name
                
                if item['type'] == 'FILE':
                    webhdfs_url = f"http://{namenode_host}:{webhdfs_port}/webhdfs/v1{hdfs_path}"
                    params = { "op": "OPEN" }
                    # 发起请求
                    with requests.get(webhdfs_url, params=params, stream=True) as r:
                        r.raise_for_status()
                        with open(local_path, "wb") as f:
                            for chunk in r.iter_content(chunk_size=8192):
                                f.write(chunk)
            logger.info(f'hdfs文件下载完毕，共下载 {len(files)} 个文件')
                    
        except requests.exceptions.RequestException as e:
            logger.error(f"Error accessing {hdfs_dir}: {str(e)}")


    def merge_parquet(
        self,
        tmp_output_path: Path,
        output_path: str,
    ):
        """
        使用 PyArrow 高效合并 Parquet 文件
        
        参数:
            input_files: Parquet 文件路径列表
            output_path: 输出文件路径
        """
        input_files = [tmp_output_path / file.name for file in tmp_output_path.iterdir() if file.is_file() and file.name.endswith('parquet')]
        
        # 读取第一个文件获取 schema
        first_table = pq.read_table(input_files[0])
        
        # 创建写入器
        writer = pq.ParquetWriter(
            output_path,
            schema=first_table.schema,
            compression="ZSTD",  # 更高效的压缩
        )
        
        # 写入第一个表
        writer.write_table(first_table)
        
        # 追加写入其他文件
        for file in input_files[1:]:
            table = pq.read_table(file)
            writer.write_table(table)
        
        # 关闭写入器
        writer.close()
        logger.info(f"合并完成: {output_path}")

    def _execute_with_jdbc(
        self,
        sql: str,
        output_path: Path
    ) -> Tuple[int, int, int]:
        """使用JDBC执行查询并保存（原有逻辑）
        
        Args:
            sql: Spark SQL查询语句
            output_path: 输出文件路径

        Returns:
            (row_count, column_count, file_size_bytes)
        """
        from utils.spark_utils import spark_utils
        
        logger.info(f"使用JDBC执行Spark查询并保存到: {output_path}")

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
        etl_date_str: str
    ) -> Path:
        """生成宽表文件路径

        Args:
            wide_table_name: 宽表名称
            version_hash: 版本号
            etl_date: ETL日期

        Returns:
            文件路径
        """
        filename = f"{wide_table_name}_{version_hash}_{etl_date_str}.parquet"

        # 存储在子目录: {storage_path}/{wide_table_name}/
        table_dir = self.storage_path / wide_table_name
        return table_dir / filename

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
