"""PostgreSQL分析数据库工具类"""

from datetime import date, timedelta, datetime
from contextlib import contextmanager
from typing import Optional, Any, List, Tuple, Dict

import pandas as pd
from loguru import logger
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from utils.config import settings


def _get_pg_config() -> Dict[str, Any]:
    db_config = settings.fraudhunter_analyze_db
    if db_config['db_type'] != 'postgresql':
        raise ValueError(f"仅支持PostgreSQL, 不支持 {db_config['db_type']}")
    return db_config['postgresql']


class AnalyzeDBConnector:
    """PostgreSQL分析数据库连接器 (单例模式)"""

    _engine: Optional[Engine] = None
    _session_factory: Optional[sessionmaker] = None

    @classmethod
    def get_engine(cls) -> Engine:
        if cls._engine is None:
            pg_config = _get_pg_config()
            conn_url = (
                f"postgresql://{pg_config['user']}:{pg_config['password']}"
                f"@{pg_config['host']}:{pg_config['port']}/{pg_config['database']}"
            )
            cls._engine = create_engine(
                conn_url,
                poolclass=QueuePool,
                pool_size=pg_config.get('pool_size', 10),
                max_overflow=pg_config.get('max_overflow', 20),
                pool_recycle=pg_config.get('pool_recycle', 3600),
                pool_pre_ping=pg_config.get('pool_pre_ping', True),
                echo=False
            )
            cls._session_factory = sessionmaker(
                bind=cls._engine,
                autocommit=False,
                autoflush=False
            )
            logger.info(f"PostgreSQL引擎已初始化: {pg_config['host']}:{pg_config['port']}/{pg_config['database']}")
        return cls._engine

    @classmethod
    @contextmanager
    def get_session(cls):
        session = cls._session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"数据库会话异常: {e}", exc_info=True)
            raise
        finally:
            session.close()

    @classmethod
    def execute_sql(
        cls,
        sql: str,
        params: Optional[Dict[str, Any]] = None,
        fetch_df: bool = False
    ) -> Optional[pd.DataFrame]:
        engine = cls.get_engine()
        try:
            if fetch_df:
                return pd.read_sql_query(text(sql), engine, params=params)
            with engine.connect() as conn:
                conn.execute(text(sql), params or {})
                conn.commit()
            return None
        except SQLAlchemyError as e:
            logger.error(f"SQL执行失败: {sql}\n错误: {e}", exc_info=True)
            raise

    @classmethod
    def batch_insert(
        cls,
        table_name: str,
        df: pd.DataFrame,
        chunksize: int = 1000,
        if_exists: str = 'append'
    ) -> int:
        engine = cls.get_engine()
        try:
            rows_inserted = df.to_sql(
                table_name, engine, if_exists=if_exists,
                index=False, method='multi', chunksize=chunksize
            )
            logger.debug(f"批量插入成功: 表={table_name}, 行数={rows_inserted}")
            return rows_inserted
        except SQLAlchemyError as e:
            logger.error(f"批量插入失败: 表={table_name}, 错误: {e}", exc_info=True)
            raise

    @classmethod
    def test_connection(cls) -> bool:
        try:
            with cls.get_session() as session:
                return session.execute(text("SELECT 1")).scalar() == 1
        except Exception as e:
            logger.error(f"数据库连接测试失败: {e}", exc_info=True)
            return False


class AnalyzeDBPartitionManager:
    """PostgreSQL分区管理器"""

    @staticmethod
    def _execute_ddl(sql: str, success_msg: str, error_prefix: str) -> bool:
        engine = AnalyzeDBConnector.get_engine()
        try:
            with engine.connect() as conn:
                conn.execute(text(sql))
                conn.commit()
            logger.debug(success_msg)
            return True
        except SQLAlchemyError as e:
            logger.error(f"{error_prefix}: {e}", exc_info=True)
            return False

    @staticmethod
    def create_partitioned_table(
        table_name: str,
        columns: List[Tuple[str, str]],
        partition_column: str = 'etl_date'
    ) -> bool:
        columns_sql = ",\n    ".join(f"{name} {typ}" for name, typ in columns)
        sql = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                {columns_sql},
                created_at timestamptz DEFAULT now()
            ) PARTITION BY RANGE ({partition_column});
        """
        return AnalyzeDBPartitionManager._execute_ddl(
            sql, f"分区表创建成功: {table_name}", f"分区表创建失败: {table_name}"
        )

    @staticmethod
    def _get_partition_name(table_name: str, partition_date: date) -> str:
        return f"{table_name}_{partition_date.strftime('%Y%m%d')}"

    @staticmethod
    def create_partition(table_name: str, partition_date: date) -> bool:
        partition_name = AnalyzeDBPartitionManager._get_partition_name(table_name, partition_date)
        start_date = partition_date.strftime('%Y-%m-%d')
        end_date = (partition_date + timedelta(days=1)).strftime('%Y-%m-%d')
        sql = f"""
            CREATE TABLE IF NOT EXISTS {partition_name}
            PARTITION OF {table_name}
            FOR VALUES FROM ('{start_date}') TO ('{end_date}');
        """
        return AnalyzeDBPartitionManager._execute_ddl(
            sql, f"分区创建成功: {partition_name}", f"分区创建失败: {partition_name}"
        )

    @staticmethod
    def drop_partition(table_name: str, partition_date: date) -> bool:
        partition_name = AnalyzeDBPartitionManager._get_partition_name(table_name, partition_date)
        sql = f"DROP TABLE IF EXISTS {partition_name};"
        return AnalyzeDBPartitionManager._execute_ddl(
            sql, f"分区删除成功: {partition_name}", f"分区删除失败: {partition_name}"
        )

    @staticmethod
    def partition_exists(table_name: str, partition_date: date) -> bool:
        engine = AnalyzeDBConnector.get_engine()
        partition_name = AnalyzeDBPartitionManager._get_partition_name(table_name, partition_date)
        sql = """
            SELECT EXISTS (
                SELECT 1 FROM pg_tables
                WHERE schemaname = 'public' AND tablename = :partition_name
            );
        """
        try:
            with engine.connect() as conn:
                return bool(conn.execute(text(sql), {"partition_name": partition_name}).scalar())
        except SQLAlchemyError as e:
            logger.error(f"分区检查失败: {partition_name}, 错误: {e}", exc_info=True)
            return False

    @staticmethod
    def ensure_partition(table_name: str, partition_date: date) -> bool:
        if not AnalyzeDBPartitionManager.partition_exists(table_name, partition_date):
            return AnalyzeDBPartitionManager.create_partition(table_name, partition_date)
        return True

    @staticmethod
    def create_realtime_tables():
        transaction_columns = [
            ("acct_no", "varchar(255)"), ("acct_open_dt", "varchar(255)"), ("acct_type", "varchar(255)"),
            ("aorm_date", "varchar(255)"), ("branch_name", "varchar(255)"), ("branch_no", "varchar(255)"),
            ("busi_typ", "varchar(255)"), ("ccy_name", "varchar(255)"), ("cha_desc", "varchar(255)"),
            ("channel", "varchar(255)"), ("class_type", "varchar(255)"), ("cp_acct_name", "varchar(255)"),
            ("cp_acct_no", "varchar(255)"), ("cp_acct_type", "varchar(255)"), ("cp_bank_branch_name", "varchar(255)"),
            ("cp_bank_num", "varchar(255)"), ("cp_class_type", "varchar(255)"), ("cp_int_cat", "varchar(255)"),
            ("currency", "varchar(255)"), ("cust_name", "varchar(255)"), ("cust_type", "varchar(255)"),
            ("customer_no", "varchar(255)"), ("fir_branch_name", "varchar(255)"), ("fir_branch_no", "varchar(255)"),
            ("gl_class_code", "varchar(255)"), ("inct_01_amount", "decimal(18,2)"), ("inct_01_balance", "decimal(18,2)"),
            ("inct_01_tran_acct", "varchar(255)"), ("inct_20_chnnel", "varchar(255)"), ("inct_20_desc", "varchar(255)"),
            ("inct_20_narr", "varchar(255)"), ("inct_20_rec_no", "varchar(255)"), ("inct_20_source", "varchar(255)"),
            ("inma_flag", "varchar(255)"), ("int_cat", "varchar(255)"), ("jrnl_no", "varchar(255)"),
            ("mgr_no", "varchar(255)"), ("mst_aom_no", "varchar(255)"), ("parent_branch_name", "varchar(255)"),
            ("parent_branch_no", "varchar(255)"), ("peri_no", "varchar(255)"), ("prd_name", "varchar(255)"),
            ("rec_no", "varchar(255)"), ("rt_processing_time", "varchar(255)"), ("send_to_fh_time", "varchar(255)"),
            ("tran_branch", "varchar(255)"), ("tran_date", "date NOT NULL"), ("tran_time", "varchar(255)"),
            ("tran_type", "varchar(255)"), ("trn_code", "varchar(255)"), ("updated_at", "timestamptz DEFAULT now()")
        ]

        AnalyzeDBPartitionManager.create_partitioned_table("realtime_oss_inct_new", transaction_columns, "tran_date")

        engine = AnalyzeDBConnector.get_engine()
        indexes = [
            f"CREATE INDEX IF NOT EXISTS idx_realtime_tran_date ON realtime_oss_inct_new (tran_date);",
            f"CREATE INDEX IF NOT EXISTS idx_realtime_acct_no ON realtime_oss_inct_new (acct_no);",
            f"CREATE INDEX IF NOT EXISTS idx_realtime_created_at ON realtime_oss_inct_new (created_at);"
        ]
        with engine.connect() as conn:
            for idx_sql in indexes:
                try:
                    conn.execute(text(idx_sql))
                    conn.commit()
                except Exception as e:
                    logger.warning(f"索引创建可能已存在: {e}")
        logger.info("实时数据基础表创建完成")

    @staticmethod
    def _map_pg_type(indicator_type: str) -> str:
        type_mapping = {
            'integer': 'integer',
            'float': 'decimal(18,2)',
            'string': 'varchar(255)',
            'date': 'date',
            'enum': 'varchar(255)',
            'boolean': 'boolean'
        }
        return type_mapping.get(indicator_type, 'varchar(255)')

    @staticmethod
    def create_wide_table(
        table_name: str,
        indicator_metadata: Dict[str, Any],
        is_realtime: bool = False
    ) -> bool:
        columns = [
            ("target_id", "varchar(255) NOT NULL"),
            ("etl_date", "date NOT NULL")
        ]
        for meta in indicator_metadata.values():
            indicator_code = meta.get('indicator_code')
            if indicator_code:
                pg_type = AnalyzeDBPartitionManager._map_pg_type(meta.get('data_type', 'string'))
                columns.append((indicator_code, pg_type))

        success = AnalyzeDBPartitionManager.create_partitioned_table(table_name, columns, "etl_date")
        if success:
            engine = AnalyzeDBConnector.get_engine()
            with engine.connect() as conn:
                conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_target_id ON {table_name} (target_id);"))
                conn.execute(text(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_etl_date ON {table_name} (etl_date);"))
                conn.commit()
            logger.info(f"宽表版本表创建成功: {table_name}, 指标数={len(indicator_metadata)}")
        return success

    @staticmethod
    def drop_table(table_name: str) -> bool:
        return AnalyzeDBPartitionManager._execute_ddl(
            f"DROP TABLE IF EXISTS {table_name} CASCADE;",
            f"表删除成功: {table_name}",
            f"表删除失败: {table_name}"
        )

    @staticmethod
    def get_old_version_tables(retention_days: int = 30) -> List[str]:
        engine = AnalyzeDBConnector.get_engine()
        cutoff_date = date.today() - timedelta(days=retention_days)
        sql = """
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
              AND tablename LIKE '%_v%'
              AND tablename NOT LIKE '%realtime%'
              AND NOT EXISTS (
                  SELECT 1 FROM fraudhunter_wide_table_snapshot
                  WHERE pg_table_name = tablename AND created_at > :cutoff_date
              );
        """
        try:
            df = pd.read_sql_query(sql, engine, params={"cutoff_date": cutoff_date})
            table_names = df['tablename'].tolist()
            logger.info(f"找到 {len(table_names)} 个超过{retention_days}天的历史版本表")
            return table_names
        except Exception as e:
            logger.error(f"查询历史版本表失败: {e}", exc_info=True)
            return []

    @staticmethod
    def list_partitions(table_name: str) -> List[str]:
        """列出表的所有分区

        Args:
            table_name: 主表名

        Returns:
            分区名列表
        """
        engine = AnalyzeDBConnector.get_engine()
        sql = """
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
              AND tablename LIKE :pattern
            ORDER BY tablename
        """
        try:
            df = pd.read_sql_query(sql, engine, params={"pattern": f"{table_name}_%"})
            partition_list = df['tablename'].tolist()
            logger.debug(f"找到表 {table_name} 的 {len(partition_list)} 个分区")
            return partition_list
        except Exception as e:
            logger.error(f"列出分区失败: {table_name}, 错误={e}", exc_info=True)
            return []

    @staticmethod
    def cleanup_old_partitions(table_name: str, retention_days: int = 7) -> int:
        """清理表的旧分区

        Args:
            table_name: 主表名
            retention_days: 保留天数

        Returns:
            删除的分区数量
        """
        cutoff_date = date.today() - timedelta(days=retention_days)
        deleted_count = 0

        # 获取所有分区
        partitions = AnalyzeDBPartitionManager.list_partitions(table_name)

        for partition_name in partitions:
            try:
                # 从分区名提取日期 (格式: table_name_YYYYMMDD)
                date_str = partition_name.split('_')[-1]
                if len(date_str) == 8 and date_str.isdigit():
                    partition_date = datetime.strptime(date_str, '%Y%m%d').date()

                    # 删除超过保留期的分区
                    if partition_date < cutoff_date:
                        sql = f"DROP TABLE IF EXISTS {partition_name};"
                        if AnalyzeDBPartitionManager._execute_ddl(
                            sql,
                            f"删除旧分区: {partition_name}",
                            f"删除分区失败: {partition_name}"
                        ):
                            deleted_count += 1
            except (ValueError, IndexError) as e:
                logger.warning(f"跳过无法解析日期的分区: {partition_name}, 错误={e}")
                continue

        if deleted_count > 0:
            logger.info(f"清理旧分区完成: 表={table_name}, 删除分区数={deleted_count}, 保留天数={retention_days}")
        else:
            logger.debug(f"没有需要清理的旧分区: 表={table_name}")

        return deleted_count

    @staticmethod
    def cleanup_expired_snapshots(wide_table_name: str, retention_days: int) -> int:
        """清理过期的宽表快照记录

        Args:
            wide_table_name: 宽表名称
            retention_days: 保留天数

        Returns:
            删除的快照数量
        """
        from models.db_base import get_db_session
        from models.fraudhunter.wide_table import FraudHunterWideTableSnapshot
        from sqlalchemy import and_

        cutoff_date = date.today() - timedelta(days=retention_days)

        try:
            with get_db_session() as db:
                expired_snapshots = db.query(FraudHunterWideTableSnapshot).filter(
                    and_(
                        FraudHunterWideTableSnapshot.wide_table_name == wide_table_name,
                        FraudHunterWideTableSnapshot.etl_date < cutoff_date
                    )
                ).all()

                deleted_count = len(expired_snapshots)
                for snapshot in expired_snapshots:
                    db.delete(snapshot)
                db.commit()

                if deleted_count > 0:
                    logger.info(
                        f"清理过期快照完成: 表={wide_table_name}, "
                        f"删除记录数={deleted_count}, 保留天数={retention_days}"
                    )
                else:
                    logger.debug(f"没有需要清理的过期快照: 表={wide_table_name}")

                return deleted_count

        except Exception as e:
            logger.error(f"清理过期快照失败: 表={wide_table_name}, 错误={e}", exc_info=True)
            return 0

    @staticmethod
    def cleanup_orphaned_snapshots() -> int:
        """清理孤立的快照记录 (对应PG表已不存在的快照)

        将对应表已不存在的快照记录状态标记为deleted

        Returns:
            标记为deleted的快照数量
        """
        from models.db_base import get_db_session
        from models.fraudhunter.wide_table import FraudHunterWideTableSnapshot

        try:
            with get_db_session() as db:
                # 只查询ready状态的快照记录
                snapshots = db.query(FraudHunterWideTableSnapshot).filter(
                    FraudHunterWideTableSnapshot.status == 'ready'
                ).all()

                marked_count = 0
                engine = AnalyzeDBConnector.get_engine()

                for snapshot in snapshots:
                    if snapshot.parquet_file_path:
                        table_name = snapshot.parquet_file_path

                        # 检查PG表是否存在
                        check_sql = """
                            SELECT EXISTS (
                                SELECT 1 FROM pg_tables
                                WHERE schemaname = 'public' AND tablename = :table_name
                            );
                        """

                        try:
                            with engine.connect() as conn:
                                table_exists = bool(conn.execute(
                                    text(check_sql),
                                    {"table_name": table_name}
                                ).scalar())

                                # 如果表不存在，将状态标记为deleted
                                if not table_exists:
                                    snapshot.status = 'deleted'
                                    marked_count += 1
                                    logger.debug(
                                        f"标记孤立快照为deleted: id={snapshot.id}, "
                                        f"表={table_name}"
                                    )

                        except Exception as e:
                            logger.warning(f"检查表存在性失败: {table_name}, 错误={e}")
                            continue

                if marked_count > 0:
                    db.commit()
                    logger.info(f"清理孤立快照完成: 标记 {marked_count} 条记录为deleted")
                else:
                    logger.debug("没有需要标记为deleted的孤立快照")

                return marked_count

        except Exception as e:
            logger.error(f"清理孤立快照失败: {e}", exc_info=True)
            return 0


def get_analyze_db_session() -> Session:
    return AnalyzeDBConnector.get_session()


def execute_analyze_sql(sql: str, params: Optional[Dict[str, Any]] = None) -> Optional[pd.DataFrame]:
    return AnalyzeDBConnector.execute_sql(sql, params=params, fetch_df=True)
