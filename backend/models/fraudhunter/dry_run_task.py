"""
FraudHunter任务执行相关数据库模型（Dry Run专用）
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Date, Index
from datetime import datetime
from models.db_base import Base


class FraudHunterDryRunExecution(Base):
    """Dry Run执行记录表（合并原 TaskExecution 和 TaskExecutionRecord）"""
    __tablename__ = "fraudhunter_dryrun_execution"

    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键ID')

    # 任务信息
    task_type = Column(String(32), nullable=False, comment='任务类型：indicator/model')
    task_id = Column(Integer, nullable=False, comment='任务关联ID（指标组ID或模型ID）')
    execution_id = Column(String(64), unique=True, nullable=False, comment='执行ID（UUID）')
    parent_execution_id = Column(String(64), nullable=True, comment='父执行ID（批量任务关联子任务）')

    # 执行详情
    etl_date = Column(Date, comment='ETL日期')
    version = Column(Integer, comment='执行版本号')

    # 执行信息
    start_time = Column(DateTime, comment='开始时间')
    end_time = Column(DateTime, comment='结束时间')

    # 状态
    status = Column(String(16), default='pending', comment='状态：pending/running/success/failed/cancelled')

    # 执行参数
    parameters = Column(JSON, comment='执行参数（配置、环境变量等）')

    # 执行日志
    log_content = Column(Text, comment='执行日志')
    error_message = Column(Text, comment='错误信息')

    # 执行统计
    rows_processed = Column(Integer, comment='处理行数')
    rows_output = Column(Integer, comment='输出行数')
    duration_seconds = Column(Integer, comment='执行时长（秒）')

    # 执行结果
    result_summary = Column(JSON, comment='结果摘要（处理记录数、命中数等）')

    # 审计字段
    created_by = Column(String(64), comment='触发人')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')

    # 索引
    __table_args__ = (
        Index('idx_fh_dryrun_type_id', 'task_type', 'task_id'),
        Index('idx_fh_dryrun_execution_id', 'execution_id'),
        Index('idx_fh_dryrun_parent_execution_id', 'parent_execution_id'),
        Index('idx_fh_dryrun_status', 'status'),
        Index('idx_fh_dryrun_etl_date', 'etl_date'),
        Index('idx_fh_dryrun_created_at', 'created_at'),
    )

    def __repr__(self):
        return f"<FraudHunterDryRunExecution(id={self.id}, execution_id='{self.execution_id}', status='{self.status}')>"
