"""
FraudHunter模型相关数据库模型
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Index, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from models.db_base import Base


class FraudHunterModelDefinition(Base):
    """模型定义表"""
    __tablename__ = "fraudhunter_model_definition"

    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键ID')

    # 基本信息
    model_code = Column(String(64), unique=True, nullable=False, comment='模型编码')
    model_name = Column(String(128), nullable=False, comment='模型名称')
    description = Column(Text, comment='模型描述')

    offline_model_sql = Column(Text, comment='离线模型SQL，由模型规则生成')
    realtime_model_sql = Column(Text, comment='实时模型SQL，由模型规则生成')

    is_send_alert_message = Column(Boolean, default=False, comment='是否发送告警消息')
    alert_message_target = Column(String(256), comment='告警消息目标')
    is_acct_control = Column(Boolean, default=False, comment='是否账户控制')

    # 模型规则（JSON格式存储可视化定义）
    rule_config = Column(JSON, nullable=False, comment='规则配置JSON')

    # 关联指标
    indicator_codes = Column(Text, comment='使用的指标编码列表，JSON数组')

    # 版本管理
    current_version = Column(Integer, default=1, comment='当前发布版本')
    latest_version = Column(Integer, default=1, comment='最新版本号')

    # 状态管理
    status = Column(String(16), default='draft', comment='状态：draft/testing/online/offline/archived')

    # 审计字段
    created_by = Column(String(64), comment='创建人')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_by = Column(String(64), comment='更新人')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    # 关系
    histories = relationship("FraudHunterModelHistory", back_populates="model", cascade="all, delete-orphan")

    # 索引
    __table_args__ = (
        Index('idx_fh_model_code', 'model_code'),
        Index('idx_fh_model_status', 'status'),
    )

    def __repr__(self):
        return f"<FraudHunterModelDefinition(id={self.id}, model_code='{self.model_code}', status='{self.status}')>"


class FraudHunterModelHistory(Base):
    """模型定义版本历史表"""
    __tablename__ = "fraudhunter_model_history"

    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键ID')
    model_id = Column(Integer, ForeignKey('fraudhunter_model_definition.id'), nullable=False, comment='模型ID')
    version = Column(Integer, nullable=False, comment='版本号')

    # 历史快照
    model_code = Column(String(64), nullable=False, comment='模型编码')
    model_name = Column(String(128), nullable=False, comment='模型名称')
    description = Column(Text, comment='描述')
    rule_config = Column(JSON, comment='规则配置')
    indicator_codes = Column(Text, comment='指标编码列表')
    output_table = Column(String(128), comment='输出表名')
    output_partition_field = Column(String(64), comment='分区字段')
    generated_code = Column(Text, comment='生成的代码')

    # 变更信息
    change_type = Column(String(16), nullable=False, comment='变更类型：create/update/publish/archive')
    change_description = Column(Text, comment='变更说明')

    # 审计字段
    created_by = Column(String(64), comment='创建人')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')

    # 关系
    model = relationship("FraudHunterModelDefinition", back_populates="histories")

    # 索引
    __table_args__ = (
        Index('uk_fh_model_version', 'model_id', 'version', unique=True),
        Index('idx_fh_modelhist_model_id', 'model_id'),
        Index('idx_fh_modelhist_created_at', 'created_at'),
    )

    def __repr__(self):
        return f"<FraudHunterModelHistory(id={self.id}, model_id={self.model_id}, version={self.version})>"
