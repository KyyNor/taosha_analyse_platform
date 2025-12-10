"""
FraudHunter宽表版本管理相关模型
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Date, BigInteger, Index, ForeignKey, JSON
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime
from typing import Optional, Dict
from models.db_base import Base


class FraudHunterIndicatorRunProgress(Base):
    """指标运行进度表

    记录每次DS任务执行的完成时间，由DS任务末尾Shell脚本回调API更新
    """
    __tablename__ = "fraudhunter_indicator_run_progress"

    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment='主键ID')

    # 指标任务关联
    indicator_task_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('fraudhunter_indicator_task.id'),
        nullable=False,
        comment='指标任务ID'
    )

    # 版本信息
    indicator_version: Mapped[int] = mapped_column(Integer, nullable=False, comment='指标版本号')

    # ETL信息
    etl_date: Mapped[Date] = mapped_column(Date, nullable=False, comment='ETL日期')

    # 完成时间
    finish_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment='完成时间')

    # 审计字段
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment='更新时间'
    )

    # 索引
    __table_args__ = (
        # 复合唯一索引: 同一任务同一日期同一版本只能有一条记录
        Index(
            'uk_fh_run_task_date_version',
            'indicator_task_id',
            'etl_date',
            'indicator_version',
            unique=True
        ),
        # 查询优化索引
        Index('idx_fh_run_task_id', 'indicator_task_id'),
        Index('idx_fh_run_etl_date', 'etl_date'),
    )

    def __repr__(self):
        return (
            f"<FraudHunterIndicatorRunProgress("
            f"id={self.id}, "
            f"task_id={self.indicator_task_id}, "
            f"etl_date={self.etl_date}, "
            f"version={self.indicator_version})>"
        )


class FraudHunterWideTableVersion(Base):
    """指标宽表版本变更表

    管理离线指标宽表的版本号和状态流转
    按object_type分组管理版本（dep_acct_wide_table/cust_wide_table/loan_acct_wide_table等）
    """
    __tablename__ = "fraudhunter_wide_table_version"

    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment='主键ID')

    # 宽表标识（根据object_type决定）
    wide_table_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment='宽表名称: dep_acct_wide_table/cust_wide_table/loan_acct_wide_table'
    )

    # 版本号（完整64位SHA256 hash）
    version_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        comment='版本号(SHA256 hash取前8位)'
    )

    # 参与指标元数据（JSON格式）
    indicator_metadata: Mapped[Dict] = mapped_column(
        JSON,
        nullable=False,
        comment='参与指标的元数据 {indicator_id: {version, indicator_code, indicator_name, indicator_task_id}}'
    )

    # 状态管理
    status: Mapped[str] = mapped_column(
        String(16),
        default='target',
        nullable=False,
        comment='状态: current/target/history/skipped'
    )

    # 状态流转时间
    target_at: Mapped[Optional[datetime]] = mapped_column(DateTime, comment='成为target的时间')
    current_at: Mapped[Optional[datetime]] = mapped_column(DateTime, comment='成为current的时间')
    history_at: Mapped[Optional[datetime]] = mapped_column(DateTime, comment='成为history的时间')
    skipped_at: Mapped[Optional[datetime]] = mapped_column(DateTime, comment='成为skipped的时间')

    # 审计字段
    created_by: Mapped[Optional[str]] = mapped_column(String(64), comment='创建人')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment='更新时间'
    )

    # 关系
    snapshots: Mapped[list["FraudHunterWideTableSnapshot"]] = relationship(
        "FraudHunterWideTableSnapshot",
        back_populates="version",
        cascade="all, delete-orphan"
    )

    # 索引
    __table_args__ = (
        Index('idx_fh_wv_table_name', 'wide_table_name'),
        Index('idx_fh_wv_version_hash', 'version_hash'),
        Index('idx_fh_wv_status', 'status'),
        Index('idx_fh_wv_created_at', 'created_at'),
    )

    def __repr__(self):
        return (
            f"<FraudHunterWideTableVersion("
            f"id={self.id}, "
            f"table='{self.wide_table_name}', "
            f"version_hash='{self.version_hash[:8]}...', "
            f"status='{self.status}')>"
        )


class FraudHunterWideTableSnapshot(Base):
    """指标宽表快照记录表

    记录每个ETL日期的宽表文件信息
    """
    __tablename__ = "fraudhunter_wide_table_snapshot"

    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment='主键ID')

    # 宽表标识
    wide_table_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment='宽表名称: dep_acct_wide_table/cust_wide_table等'
    )

    # ETL日期
    etl_date: Mapped[Date] = mapped_column(Date, nullable=False, comment='ETL日期')

    # 版本号（实时指标为NULL）
    version_hash: Mapped[Optional[str]] = mapped_column(
        String(64),
        ForeignKey('fraudhunter_wide_table_version.version_hash'),
        comment='版本号(实时指标为NULL)'
    )

    # 文件信息
    parquet_file_path: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        comment='Parquet文件路径'
    )
    file_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, comment='文件大小(字节)')

    # 数据统计
    row_count: Mapped[Optional[int]] = mapped_column(Integer, comment='行数')
    column_count: Mapped[Optional[int]] = mapped_column(Integer, comment='列数')

    # 状态
    status: Mapped[str] = mapped_column(
        String(16),
        default='generating',
        nullable=False,
        comment='状态: generating/ready/failed/deleted'
    )

    # 生成时间
    generation_time: Mapped[Optional[datetime]] = mapped_column(DateTime, comment='生成时间')

    # 错误信息
    error_message: Mapped[Optional[str]] = mapped_column(Text, comment='错误信息')

    # 审计字段
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment='更新时间'
    )

    # 关系
    version: Mapped[Optional["FraudHunterWideTableVersion"]] = relationship(
        "FraudHunterWideTableVersion",
        back_populates="snapshots"
    )

    # 索引
    __table_args__ = (
        # 复合唯一索引: 同一宽表同一日期只能有一条记录
        Index('uk_fh_ws_table_date', 'wide_table_name', 'version_hash', 'etl_date', unique=True),
        Index('idx_fh_ws_table_name', 'wide_table_name'),
        Index('idx_fh_ws_etl_date', 'etl_date'),
        Index('idx_fh_ws_version_hash', 'version_hash'),
        Index('idx_fh_ws_status', 'status'),
        Index('idx_fh_ws_created_at', 'created_at'),
    )

    def __repr__(self):
        return (
            f"<FraudHunterWideTableSnapshot("
            f"id={self.id}, "
            f"table='{self.wide_table_name}', "
            f"etl_date={self.etl_date}, "
            f"status='{self.status}')>"
        )
