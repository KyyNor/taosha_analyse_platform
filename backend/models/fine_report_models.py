"""
FineReport报表元数据相关的SQLAlchemy模型
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Enum, Index
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from .db_base import Base


class MetadataFineReport(Base):
    """FineReport报表元数据模型"""
    __tablename__ = "metadata_fine_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    report_cpt_path: Mapped[str] = mapped_column(Text, nullable=False)
    report_type: Mapped[str] = mapped_column(Enum('summary', 'detail'), nullable=False)
    report_design_address: Mapped[str] = mapped_column(String(255), nullable=False)
    report_mount_path: Mapped[str] = mapped_column(String(500), nullable=True)  # 报表挂载路径
    report_mount_type: Mapped[str] = mapped_column(
        Enum('normal', 'removed'),
        nullable=False,
        default='normal'
    )  # 报表挂载方式: normal=正常, removed=已移除
    department_id: Mapped[int] = mapped_column(Integer, nullable=True, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    usage_scenario: Mapped[str] = mapped_column(Text, default="")
    is_available: Mapped[int] = mapped_column(Integer, default=0)  # 0=可用，1=不可用
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<MetadataFineReport(id={self.id}, name='{self.report_name}', type='{self.report_type}', mount_type='{self.report_mount_type}')>"
