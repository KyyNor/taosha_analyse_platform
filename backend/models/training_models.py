"""
训练数据相关的SQLAlchemy模型
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from .db_base import Base


class TrainingData(Base):
    """训练数据模型 - 存储NL转SQL的训练示例

    用于存储自然语言查询和对应的SQL语句对，以及相关的元信息
    """
    __tablename__ = "training_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 基本信息
    question: Mapped[str] = mapped_column(Text, nullable=False, index=True)  # 自然语言问题
    sql: Mapped[str] = mapped_column(Text, nullable=False)  # 对应的SQL查询

    # 分类和元数据
    category: Mapped[str] = mapped_column(String(100), default="general", index=True)  # 查询类别（如：select, join, aggregate等）
    difficulty: Mapped[str] = mapped_column(String(50), default="medium", index=True)  # 难度等级：easy, medium, hard
    tags: Mapped[str] = mapped_column(Text, default="")  # 标签列表，JSON格式或逗号分隔

    # 质量评分
    quality_score: Mapped[float] = mapped_column(Float, default=0.5)  # 0.0-1.0的质量评分
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否已验证
    verification_notes: Mapped[str] = mapped_column(Text, default="")  # 验证备注

    # 使用统计
    usage_count: Mapped[int] = mapped_column(Integer, default=0)  # 被使用次数
    success_count: Mapped[int] = mapped_column(Integer, default=0)  # 成功执行次数

    # 管理信息
    source: Mapped[str] = mapped_column(String(100), default="manual")  # 来源：manual, generated, imported等
    created_by: Mapped[str] = mapped_column(String(100), default="system")  # 创建者
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<TrainingData(id={self.id}, category='{self.category}', difficulty='{self.difficulty}')>"


class TrainingSession(Base):
    """训练会话模型 - 记录每次模型训练的信息

    用于跟踪Vanna模型的训练过程，记录训练统计和结果
    """
    __tablename__ = "training_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 基本信息
    session_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)  # 训练会话名称
    session_type: Mapped[str] = mapped_column(String(50), default="manual", index=True)  # 类型：manual, auto, scheduled

    # 训练数据统计
    total_samples: Mapped[int] = mapped_column(Integer, default=0)  # 总样本数
    successful_samples: Mapped[int] = mapped_column(Integer, default=0)  # 成功训练样本数
    failed_samples: Mapped[int] = mapped_column(Integer, default=0)  # 失败样本数

    # 训练结果
    status: Mapped[str] = mapped_column(String(50), default="pending", index=True)  # 状态：pending, running, completed, failed
    success_rate: Mapped[float] = mapped_column(Float, default=0.0)  # 成功率 (0.0-1.0)
    training_time_seconds: Mapped[float] = mapped_column(Float, default=0.0)  # 训练耗时（秒）

    # 性能指标
    average_confidence: Mapped[float] = mapped_column(Float, default=0.0)  # 平均置信度
    model_version: Mapped[str] = mapped_column(String(100), default="")  # 模型版本

    # 管理信息
    created_by: Mapped[str] = mapped_column(String(100), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)  # 开始训练时间
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)  # 完成时间

    # 备注
    notes: Mapped[str] = mapped_column(Text, default="")  # 训练备注

    def __repr__(self):
        return f"<TrainingSession(id={self.id}, name='{self.session_name}', status='{self.status}')>"


class TrainingMetrics(Base):
    """训练指标模型 - 记录训练过程中的详细指标

    用于保存每次训练的详细性能指标，便于分析和对比
    """
    __tablename__ = "training_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 关联训练会话
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("training_sessions.id"), nullable=False, index=True)

    # 性能指标
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # 指标名称
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)  # 指标值
    metric_type: Mapped[str] = mapped_column(String(50), default="performance")  # 指标类型：performance, accuracy, latency等

    # 详细信息
    description: Mapped[str] = mapped_column(Text, default="")  # 指标描述
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"<TrainingMetrics(id={self.id}, session_id={self.session_id}, metric='{self.metric_name}')>"


class SQLValidationResult(Base):
    """SQL验证结果模型 - 记录SQL查询的执行和验证情况

    用于跟踪SQL查询在训练或使用中的验证结果
    """
    __tablename__ = "sql_validation_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 关联训练数据
    training_data_id: Mapped[int] = mapped_column(Integer, ForeignKey("training_data.id"), nullable=True, index=True)

    # 查询信息
    original_sql: Mapped[str] = mapped_column(Text, nullable=False)  # 原始SQL
    executed_sql: Mapped[str] = mapped_column(Text, nullable=False)  # 执行的SQL
    execution_status: Mapped[str] = mapped_column(String(50), default="pending", index=True)  # 执行状态：pending, success, error

    # 验证结果
    is_valid: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否有效
    validation_message: Mapped[str] = mapped_column(Text, default="")  # 验证信息
    error_message: Mapped[str] = mapped_column(Text, default="")  # 错误信息

    # 执行信息
    execution_time_ms: Mapped[float] = mapped_column(Float, default=0.0)  # 执行耗时（毫秒）
    row_count: Mapped[int] = mapped_column(Integer, default=0)  # 返回的行数

    # 管理信息
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)

    def __repr__(self):
        return f"<SQLValidationResult(id={self.id}, status='{self.execution_status}', valid={self.is_valid})>"
