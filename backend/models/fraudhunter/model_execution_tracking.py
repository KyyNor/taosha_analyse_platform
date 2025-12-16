"""
FraudHunter模型执行跟踪相关模型
"""

from sqlalchemy import Column, BigInteger, Integer, String, Text, DateTime, Date, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from models.db_base import Base


class FraudHunterModelExecution(Base):
    """实时模型执行记录表"""
    __tablename__ = "fraudhunter_model_execution"

    # 主键
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键ID')

    # 宽表路径信息
    realtime_dep_acct_wide_table_path = Column(String(512), nullable=False, comment='实时存款宽表路径')
    offline_dep_acct_wide_table_path = Column(String(512), nullable=False, comment='离线存款宽表路径')
    offline_cust_wide_table_path = Column(String(512), comment='离线客户宽表路径')

    # 模型信息（JSON格式：[{id, name, version, code}, ...]）
    online_models_info = Column(JSON, nullable=False, comment='所有上线模型信息（id/名称/版本/编码）')

    # 生成的SQL
    generated_sql = Column(Text, nullable=False, comment='生成的模型匹配SQL')

    # 执行时间
    execution_start_time = Column(DateTime, nullable=False, comment='执行开始时间')
    execution_end_time = Column(DateTime, comment='执行结束时间')

    # 执行结果统计
    total_hit_accounts = Column(Integer, default=0, comment='执行命中账户数')
    new_hit_accounts = Column(Integer, default=0, comment='执行新命中账户数（当日第一次命中）')

    # 执行状态
    status = Column(String(16), default='running', comment='执行状态：running/success/failed')
    error_message = Column(Text, comment='错误信息')

    # 审计字段
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    # 关系
    hit_records = relationship(
        "FraudHunterModelHitRecord",
        back_populates="execution",
        cascade="all, delete-orphan"
    )

    # 索引
    __table_args__ = (
        Index('idx_fh_realtime_exec_start_time', 'execution_start_time'),
        Index('idx_fh_realtime_exec_status', 'status'),
        Index('idx_fh_realtime_exec_created_at', 'created_at'),
        {'comment': '实时模型执行记录表'}
    )

    def __repr__(self):
        return f"<FraudHunterModelExecution(id={self.id}, start_time='{self.execution_start_time}', status='{self.status}')>"


class FraudHunterModelHitRecord(Base):
    """模型运行命中记录表"""
    __tablename__ = "fraudhunter_model_hit_record"

    # 主键
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键ID')

    # 关联执行记录
    execution_id = Column(
        BigInteger,
        ForeignKey('fraudhunter_model_execution.id'),
        comment='实时模型执行记录ID'
    )

    # 基本信息
    account_id = Column(String(64), nullable=False, comment='账号标识')
    hit_time = Column(DateTime, nullable=False, comment='命中时间')

    # 命中模型信息
    hit_model_ids = Column(JSON, nullable=False, comment='命中模型ID列表')
    hit_model_names = Column(JSON, nullable=False, comment='命中模型名称列表')

    # 指标数据
    indicator_data = Column(JSON, nullable=False, comment='指标数据')

    # 审计字段
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    # 关系
    execution = relationship("FraudHunterModelExecution", back_populates="hit_records")
    alert_control_records = relationship(
        "FraudHunterModelAlertControlRecord",
        back_populates="hit_record",
        cascade="all, delete-orphan"
    )

    # 索引
    __table_args__ = (
        Index('idx_fh_hit_execution_id', 'execution_id'),
        Index('idx_fh_hit_account_id', 'account_id'),
        Index('idx_fh_hit_hit_time', 'hit_time'),
        Index('idx_fh_hit_created_at', 'created_at'),
        {'comment': '模型运行命中记录表'}
    )

    def __repr__(self):
        return f"<FraudHunterModelHitRecord(id={self.id}, account_id='{self.account_id}', hit_time='{self.hit_time}')>"


class FraudHunterModelAlertControlRecord(Base):
    """模型告警与管控记录表"""
    __tablename__ = "fraudhunter_model_alert_control_record"

    # 主键
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键ID')

    # 关联信息
    execution_id = Column(
        BigInteger,
        ForeignKey('fraudhunter_model_execution.id'),
        comment='实时模型执行记录ID'
    )
    hit_record_id = Column(BigInteger, ForeignKey('fraudhunter_model_hit_record.id'), nullable=False, comment='命中记录ID')
    account_id = Column(String(64), nullable=False, comment='账号标识')
    record_date = Column(Date, nullable=False, comment='记录日期')

    # 模型信息（JSON数组格式）
    hit_model_ids = Column(JSON, nullable=False, comment='命中模型ID列表')
    hit_model_names = Column(JSON, nullable=False, comment='命中模型名称列表')

    # 告警相关字段
    alert_status = Column(String(16), default='not_configured', comment='告警状态：not_configured/sent/duplicate')
    alert_message = Column(Text, comment='告警消息内容')
    alert_person = Column(String(64), comment='告警人')
    alert_time = Column(DateTime, comment='告警时间')

    # 管控相关字段
    control_status = Column(String(16), default='not_configured', comment='管控状态：not_configured/executed/duplicate')
    control_time = Column(DateTime, comment='管控时间')
    control_serial_number = Column(String(64), comment='管控流水号')

    # 审计字段
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    # 关系
    hit_record = relationship("FraudHunterModelHitRecord", back_populates="alert_control_records")

    # 索引
    __table_args__ = (
        Index('idx_fh_alert_execution_id', 'execution_id'),
        Index('idx_fh_alert_account_date', 'account_id', 'record_date'),
        Index('idx_fh_alert_alert_time', 'alert_time'),
        Index('idx_fh_alert_control_time', 'control_time'),
        Index('idx_fh_alert_hit_record_id', 'hit_record_id'),
        Index('idx_fh_alert_alert_status', 'alert_status'),
        Index('idx_fh_alert_control_status', 'control_status'),
        {'comment': '模型告警与管控记录表'}
    )

    def __repr__(self):
        return f"<FraudHunterModelAlertControlRecord(id={self.id}, account_id='{self.account_id}', hit_model_ids={self.hit_model_ids}, record_date='{self.record_date}')>"
    
class FraudHunterSystemConfig(Base):
    """系统热配置表

    用于存储系统级别的动态配置，包括：
    - SQL变量：用于指标任务SQL中的 ${变量} 替换
    - 系统参数：通知人员清单、消息模板等
    """
    __tablename__ = "fraudhunter_system_config"

    # 主键
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键ID')

    # 分类
    config_category = Column(String(32), nullable=False, comment='配置分类: sql_variable/system_param')

    # 配置标识
    config_key = Column(String(64), nullable=False, unique=True, comment='配置键（唯一）')
    config_desc = Column(String(256), nullable=False, comment='配置描述')

    # 值类型和值
    config_type = Column(String(32), nullable=False, comment='值类型: string/list/json_list')
    config_value = Column(JSON, nullable=False, comment='配置值')

    # SQL转换选项（仅对list类型有效）
    sql_in_convert = Column(Integer, default=0, comment='列表是否转换为SQL IN格式（0:否 1:是）')

    # 排序
    sort_order = Column(Integer, default=0, comment='排序顺序')

    # 审计字段
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    # 索引
    __table_args__ = (
        Index('idx_fh_sys_config_category', 'config_category'),
        Index('idx_fh_sys_config_key', 'config_key'),
        {'comment': '系统热配置表'}
    )

    def __repr__(self):
        return f"<FraudHunterSystemConfig(id={self.id}, config_key='{self.config_key}', config_type='{self.config_type}')>"


# 保留旧类名作为别名，确保兼容性（可在迁移完成后删除）
FraudHunterModelUserVariableConfig = FraudHunterSystemConfig
