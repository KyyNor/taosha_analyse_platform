"""
关联字段配置相关的SQLAlchemy模型
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Index
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime
from .base import Base


class RelationFieldConfig(Base):
    """关联字段配置模型"""
    __tablename__ = "relation_field_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    relation_family: Mapped[str] = mapped_column(String(255), nullable=False)
    relation_subfamily: Mapped[str] = mapped_column(String(255), nullable=False)
    relation_desc: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 复合索引
    __table_args__ = (
        Index('idx_relation_family_subfamily', 'relation_family', 'relation_subfamily', unique=True),
        {"mysql_charset": "utf8mb4"},
    )

    # 关系定义
    columns: Mapped[list["MetadataColumn"]] = relationship(
        "MetadataColumn", back_populates="relation_config"
    )

    @property
    def relation_id(self) -> str:
        """生成关系ID字符串（保持向后兼容）"""
        return f"{self.relation_family}|{self.relation_subfamily}"

    def __repr__(self):
        return f"<RelationFieldConfig(id={self.id}, family='{self.relation_family}', subfamily='{self.relation_subfamily}')>"