"""
训练记录相关的SQLAlchemy模型 - 简化的增量训练记录系统
"""

from sqlalchemy import Column, Integer, String, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from .db_base import Base


class TrainingRecord(Base):
    """训练记录模型 - 记录各类资源的训练状态和时间

    用于跟踪不同类型资源的训练状态，支持增量训练
    """
    __tablename__ = "training_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 资源信息
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # glossary, prompt_template, relation, table
    resource_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # 对应资源表的主键ID

    # 训练时间
    last_trained_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)  # 上次训练时间
    last_modified_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)  # 资源最后修改时间

    # 状态信息
    training_status: Mapped[str] = mapped_column(String(20), default="pending", index=True)  # pending, training, completed, failed
    vector_id: Mapped[str] = mapped_column(String(255), default="", index=True)  # 向量数据库中的ID（用于删除操作）

    # 管理信息
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 复合索引 - 确保资源类型和ID的唯一性，并优化查询性能
    __table_args__ = (
        Index('idx_resource_type_id', 'resource_type', 'resource_id', unique=True),
        Index('idx_last_trained_at', 'last_trained_at'),
        Index('idx_training_status', 'training_status'),
        {"mysql_charset": "utf8mb4"},
    )

    def __repr__(self):
        return f"<TrainingRecord(type='{self.resource_type}', id={self.resource_id}, status='{self.training_status}')>"

    def update_modified_time(self, modified_time: datetime) -> None:
        """更新资源最后修改时间"""
        self.last_modified_at = modified_time
        self.updated_at = datetime.now()

    def mark_as_training(self) -> None:
        """标记为正在训练"""
        self.training_status = "training"
        self.updated_at = datetime.now()

    def update_training_time(self, vector_id: str = None) -> None:
        """更新训练完成时间"""
        self.training_status = "completed"
        self.last_trained_at = datetime.now()
        self.updated_at = datetime.now()
        if vector_id:
            self.vector_id = vector_id

    def mark_as_failed(self) -> None:
        """标记为训练失败"""
        self.training_status = "failed"
        self.updated_at = datetime.now()
