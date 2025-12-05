"""
FraudHunter指标相关模型
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Optional
from models.db_base import Base


class FraudHunterIndicatorTask(Base):
    """指标任务表（存储SQL加工逻辑）"""
    __tablename__ = "fraudhunter_indicator_task"

    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键ID')

    # 基本信息
    task_code = Column(String(64), unique=True, nullable=False, comment='指标任务编码')
    task_name = Column(String(128), nullable=False, comment='指标任务名称')
    description = Column(Text, comment='描述')

    # 加工逻辑
    logic_type = Column(String(16), default='sql', comment='逻辑类型：sql/pyspark（预留）')
    logic_content = Column(Text, nullable=False, comment='SQL内容或代码')

    # 数据源配置
    source_tables = Column(String(512), comment='依赖的源表列表，逗号分隔')

    # 版本管理
    current_version = Column(Integer, default=1, comment='当前发布版本')
    latest_version = Column(Integer, default=1, comment='最新版本号')

    # 状态管理
    status = Column(String(16), default='draft', comment='状态：draft/testing/online/offline/archived')

    # 审计字段
    created_by = Column(String(64), comment='创建人')
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    updated_by = Column(String(64), comment='更新人')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')

    # 关系
    indicators = relationship("FraudHunterIndicatorDefinition", back_populates="indicator_task", cascade="all, delete-orphan")
    histories = relationship("FraudHunterIndicatorTaskHistory", back_populates="indicator_task", cascade="all, delete-orphan")

    # 索引
    __table_args__ = (
        Index('idx_fh_task_code', 'task_code'),
        Index('idx_fh_task_status', 'status'),
    )

    def __repr__(self):
        return f"<FraudHunterIndicatorTask(id={self.id}, task_code='{self.task_code}', status='{self.status}')>"


class FraudHunterIndicatorTaskHistory(Base):
    """指标任务版本历史表"""
    __tablename__ = "fraudhunter_indicator_task_history"

    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键ID')
    task_id = Column(Integer, ForeignKey('fraudhunter_indicator_task.id'), nullable=False, comment='指标任务ID')
    version = Column(Integer, nullable=False, comment='版本号')

    # 历史快照
    task_code = Column(String(64), nullable=False, comment='指标任务编码')
    task_name = Column(String(128), nullable=False, comment='指标任务名称')
    description = Column(Text, comment='描述')
    logic_type = Column(String(16), comment='逻辑类型')
    logic_content = Column(Text, comment='SQL内容')
    source_tables = Column(String(512), comment='源表列表')

    # 变更信息
    change_type = Column(String(16), nullable=False, comment='变更类型：create/update/publish/archive')
    change_description = Column(Text, comment='变更说明')

    # 审计字段
    created_by = Column(String(64), comment='创建人')
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')

    # 关系
    indicator_task = relationship("FraudHunterIndicatorTask", back_populates="histories")

    # 索引
    __table_args__ = (
        Index('uk_fh_task_version', 'task_id', 'version', unique=True),
        Index('idx_fh_taskhist_task_id', 'task_id'),
        Index('idx_fh_taskhist_created_at', 'created_at'),
    )

    def __repr__(self):
        return f"<FraudHunterIndicatorTaskHistory(id={self.id}, task_id={self.task_id}, version={self.version})>"


class FraudHunterIndicatorDefinition(Base):
    """指标定义表"""
    __tablename__ = "fraudhunter_indicator_definition"

    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键ID')

    # 基本信息
    indicator_code = Column(String(64), unique=True, nullable=False, comment='指标编码')
    indicator_name = Column(String(128), nullable=False, comment='指标名称')
    indicator_type = Column(String(16), nullable=False, comment='指标类型：offline/realtime')
    object_type = Column(String(32), nullable=False, default='cust_no', comment='对象类型：cust_no/dep_acct_no/loan_acct_no')
    description = Column(Text, comment='指标描述')

    # 数据类型
    data_type = Column(String(16), nullable=False, comment='数据类型：numeric/enum/text/boolean')
    enum_values = Column(Text, comment='枚举值（当data_type=enum时，JSON数组格式）')

    # 指标任务关联
    indicator_task_id = Column(Integer, ForeignKey('fraudhunter_indicator_task.id'), nullable=True, comment='指标任务ID')

    # 版本管理
    current_version = Column(Integer, default=1, comment='当前发布版本')
    latest_version = Column(Integer, default=1, comment='最新版本号')

    # 状态管理
    status = Column(String(16), default='draft', comment='状态：draft/testing/online/offline/archived')

    # 审计字段
    created_by = Column(String(64), comment='创建人')
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    updated_by = Column(String(64), comment='更新人')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')

    # 关系
    indicator_task = relationship("FraudHunterIndicatorTask", back_populates="indicators")
    histories = relationship("FraudHunterIndicatorHistory", back_populates="indicator", cascade="all, delete-orphan")

    # 索引
    __table_args__ = (
        Index('idx_fh_indicator_code', 'indicator_code'),
        Index('idx_fh_indicator_task_id', 'indicator_task_id'),
        Index('idx_fh_indicator_status', 'status'),
        Index('idx_fh_indicator_type', 'indicator_type'),
        Index('idx_fh_indicator_object_type', 'object_type'),
    )

    def __repr__(self):
        return f"<FraudHunterIndicatorDefinition(id={self.id}, indicator_code='{self.indicator_code}', status='{self.status}')>"


class FraudHunterIndicatorHistory(Base):
    """指标定义版本历史表"""
    __tablename__ = "fraudhunter_indicator_history"

    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键ID')
    indicator_id = Column(Integer, ForeignKey('fraudhunter_indicator_definition.id'), nullable=False, comment='指标ID')
    version = Column(Integer, nullable=False, comment='版本号')

    # 历史快照
    indicator_code = Column(String(64), nullable=False, comment='指标编码')
    indicator_name = Column(String(128), nullable=False, comment='指标名称')
    indicator_type = Column(String(16), nullable=False, comment='指标类型')
    object_type = Column(String(32), comment='对象类型')
    description = Column(Text, comment='描述')
    data_type = Column(String(16), comment='数据类型')
    enum_values = Column(Text, comment='枚举值')
    indicator_task_id = Column(Integer, comment='指标任务ID')

    # 变更信息
    change_type = Column(String(16), nullable=False, comment='变更类型：create/update/publish/archive')
    change_description = Column(Text, comment='变更说明')

    # 审计字段
    created_by = Column(String(64), comment='创建人')
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')

    # 关系
    indicator = relationship("FraudHunterIndicatorDefinition", back_populates="histories")

    # 索引
    __table_args__ = (
        Index('uk_fh_indicator_version', 'indicator_id', 'version', unique=True),
        Index('idx_fh_indhist_indicator_id', 'indicator_id'),
        Index('idx_fh_indhist_created_at', 'created_at'),
    )

    def __repr__(self):
        return f"<FraudHunterIndicatorHistory(id={self.id}, indicator_id={self.indicator_id}, version={self.version})>"


class FraudHunterSequenceCounter(Base):
    """序列计数器表"""
    __tablename__ = "fraudhunter_sequence_counter"

    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键ID')

    # 计数器信息
    counter_type = Column(String(64), unique=True, nullable=False, comment='计数器类型')
    counter_value = Column(Integer, nullable=False, default=0, comment='当前计数值')

    # 审计字段
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')

    # 索引
    __table_args__ = (
        Index('idx_fh_counter_type', 'counter_type'),
        {'comment': '序列计数器表'}
    )

    def __repr__(self):
        return f"<FraudHunterSequenceCounter(id={self.id}, counter_type='{self.counter_type}', counter_value={self.counter_value})>"
