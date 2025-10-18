"""
元数据相关的SQLAlchemy模型
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Index
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime
from .db_base import Base

# 避免循环导入，使用字符串引用
if __name__ == "__main__":
    from .relation_models import RelationFieldConfig
    from .theme_models import ThemeTableRelation


class MetadataTable(Base):
    """元数据表模型"""
    __tablename__ = "metadata_tables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    comment: Mapped[str] = mapped_column(Text, default="")
    is_available: Mapped[int] = mapped_column(Integer, default=0)  # 0=可用，1=不可用
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系定义
    columns: Mapped[list["MetadataColumn"]] = relationship(
        "MetadataColumn", back_populates="table", cascade="all, delete-orphan"
    )
    theme_relations: Mapped[list["ThemeTableRelation"]] = relationship(
        "ThemeTableRelation", back_populates="table", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<MetadataTable(id={self.id}, name='{self.name}')>"


class MetadataColumn(Base):
    """元数据列模型"""
    __tablename__ = "metadata_columns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    table_id: Mapped[int] = mapped_column(Integer, ForeignKey("metadata_tables.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    comment: Mapped[str] = mapped_column(Text, default="")
    is_available: Mapped[int] = mapped_column(Integer, default=0)  # 0=可用，1=不可用
    business_type: Mapped[str] = mapped_column(String(255), default="")
    relation_config_id: Mapped[int] = mapped_column(Integer, ForeignKey("relation_field_config.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 复合唯一索引
    __table_args__ = (
        Index('idx_table_name_column_name', 'table_id', 'name', unique=True),
        {"mysql_charset": "utf8mb4"},
    )

    # 关系定义
    table: Mapped["MetadataTable"] = relationship("MetadataTable", back_populates="columns")
    relation_config: Mapped["RelationFieldConfig"] = relationship("RelationFieldConfig", back_populates="columns")

    def __repr__(self):
        return f"<MetadataColumn(id={self.id}, name='{self.name}', type='{self.type}')>"