"""
数据主题相关的SQLAlchemy模型
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime
from .db_base import Base


class DataTheme(Base):
    """数据主题模型"""
    __tablename__ = "data_themes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    theme_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    theme_description: Mapped[str] = mapped_column(Text, default="")
    theme_type: Mapped[str] = mapped_column(String(50), default="normal", index=True)  # normal, public
    department: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系定义
    table_relations: Mapped[list["ThemeTableRelation"]] = relationship(
        "ThemeTableRelation", back_populates="theme", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<DataTheme(id={self.id}, name='{self.theme_name}', type='{self.theme_type}')>"


class ThemeTableRelation(Base):
    """主题表关联关系模型"""
    __tablename__ = "theme_table_relations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    theme_id: Mapped[int] = mapped_column(Integer, ForeignKey("data_themes.id"), nullable=False, index=True)
    table_id: Mapped[int] = mapped_column(Integer, ForeignKey("metadata_tables.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # 复合唯一索引
    __table_args__ = (
        Index('idx_theme_table_relation', 'theme_id', 'table_id', unique=True),
        {"mysql_charset": "utf8mb4"},
    )

    # 关系定义
    theme: Mapped["DataTheme"] = relationship("DataTheme", back_populates="table_relations")
    table: Mapped["MetadataTable"] = relationship("MetadataTable", back_populates="theme_relations")

    def __repr__(self):
        return f"<ThemeTableRelation(theme_id={self.theme_id}, table_id={self.table_id})>"