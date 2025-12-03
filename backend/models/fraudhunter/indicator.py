"""
FraudHunter指标相关模型
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Optional
from models.db_base import Base


class FraudHunterIndicatorGroup(Base):
    """指标组表（存储SQL加工逻辑）"""
    __tablename__ = "fraudhunter_indicator_group"

    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键ID')

    # 基本信息
    group_code = Column(String(64), unique=True, nullable=False, comment='指标组编码')
    group_name = Column(String(128), nullable=False, comment='指标组名称')
    description = Column(Text, comment='描述')

    # 加工逻辑
    logic_type = Column(String(16), default='sql', comment='逻辑类型：sql/pyspark（预留）')
    logic_content = Column(Text, nullable=False, comment='SQL内容或代码')

    # 数据源配置
    source_tables = Column(String(512), comment='依赖的源表列表，逗号分隔')

    # 输出配置
    output_table = Column(String(128), comment='输出表名')
    output_mode = Column(String(16), default='row', comment='输出模式：row（行存）')

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
    indicators = relationship("FraudHunterIndicatorDefinition", back_populates="indicator_group", cascade="all, delete-orphan")
    histories = relationship("FraudHunterIndicatorGroupHistory", back_populates="indicator_group", cascade="all, delete-orphan")

    # 索引
    __table_args__ = (
        Index('idx_fh_group_code', 'group_code'),
        Index('idx_fh_group_status', 'status'),
    )

    def __repr__(self):
        return f"<FraudHunterIndicatorGroup(id={self.id}, group_code='{self.group_code}', status='{self.status}')>"


class FraudHunterIndicatorGroupHistory(Base):
    """指标组版本历史表"""
    __tablename__ = "fraudhunter_indicator_group_history"

    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键ID')
    group_id = Column(Integer, ForeignKey('fraudhunter_indicator_group.id'), nullable=False, comment='指标组ID')
    version = Column(Integer, nullable=False, comment='版本号')

    # 历史快照
    group_code = Column(String(64), nullable=False, comment='指标组编码')
    group_name = Column(String(128), nullable=False, comment='指标组名称')
    description = Column(Text, comment='描述')
    logic_type = Column(String(16), comment='逻辑类型')
    logic_content = Column(Text, comment='SQL内容')
    source_tables = Column(String(512), comment='源表列表')
    output_table = Column(String(128), comment='输出表名')
    output_mode = Column(String(16), comment='输出模式')

    # 变更信息
    change_type = Column(String(16), nullable=False, comment='变更类型：create/update/publish/archive')
    change_description = Column(Text, comment='变更说明')

    # 审计字段
    created_by = Column(String(64), comment='创建人')
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')

    # 关系
    indicator_group = relationship("FraudHunterIndicatorGroup", back_populates="histories")

    # 索引
    __table_args__ = (
        Index('uk_fh_group_version', 'group_id', 'version', unique=True),
        Index('idx_fh_grouphist_group_id', 'group_id'),
        Index('idx_fh_grouphist_created_at', 'created_at'),
    )

    def __repr__(self):
        return f"<FraudHunterIndicatorGroupHistory(id={self.id}, group_id={self.group_id}, version={self.version})>"


class FraudHunterIndicatorDefinition(Base):
    """指标定义表"""
    __tablename__ = "fraudhunter_indicator_definition"

    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键ID')

    # 基本信息
    indicator_code = Column(String(64), unique=True, nullable=False, comment='指标编码')
    indicator_name = Column(String(128), nullable=False, comment='指标名称')
    indicator_type = Column(String(16), nullable=False, comment='指标类型：offline/realtime')
    description = Column(Text, comment='指标描述')

    # 数据类型
    data_type = Column(String(16), nullable=False, comment='数据类型：numeric/enum/text/boolean')
    enum_values = Column(Text, comment='枚举值（当data_type=enum时，JSON数组格式）')

    # 指标组关联
    indicator_group_id = Column(Integer, ForeignKey('fraudhunter_indicator_group.id'), nullable=False, comment='指标组ID')

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
    indicator_group = relationship("FraudHunterIndicatorGroup", back_populates="indicators")
    histories = relationship("FraudHunterIndicatorHistory", back_populates="indicator", cascade="all, delete-orphan")

    # 索引
    __table_args__ = (
        Index('idx_fh_indicator_code', 'indicator_code'),
        Index('idx_fh_indicator_group_id', 'indicator_group_id'),
        Index('idx_fh_indicator_status', 'status'),
        Index('idx_fh_indicator_type', 'indicator_type'),
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
    description = Column(Text, comment='描述')
    data_type = Column(String(16), comment='数据类型')
    enum_values = Column(Text, comment='枚举值')
    indicator_group_id = Column(Integer, comment='指标组ID')

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
