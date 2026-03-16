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


class MetadataTable(Base):
    """元数据表模型"""
    __tablename__ = "metadata_tables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    comment: Mapped[str] = mapped_column(Text, default="")
    remark: Mapped[str] = mapped_column(Text, default="")
    is_available: Mapped[int] = mapped_column(Integer, default=0)  # 0=可用，1=不可用
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关系定义
    columns: Mapped[list["MetadataColumn"]] = relationship(
        "MetadataColumn", back_populates="table", cascade="all, delete-orphan"
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
    remark: Mapped[str] = mapped_column(Text, default="")
    is_available: Mapped[int] = mapped_column(Integer, default=0)  # 0=可用，1=不可用
    business_type: Mapped[str] = mapped_column(String(255), default="")
    relation_config_id: Mapped[int] = mapped_column(Integer, ForeignKey("metadata_relation_field_config.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

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


class MetadataKnowledgeDocument(Base):
    """知识文档模型 - 存储原始内容（SQL文件、文本等）"""
    __tablename__ = "metadata_knowledge_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'file', 'text', 'sql'
    source_path: Mapped[str] = mapped_column(String(500), nullable=True)  # 文件路径
    raw_content: Mapped[str] = mapped_column(Text, nullable=False)  # 原始内容
    file_size: Mapped[int] = mapped_column(Integer, nullable=True)  # 文件大小（字节）
    content_hash: Mapped[str] = mapped_column(String(64), nullable=True)  # 内容哈希（去重）
    processing_status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, processed, failed
    fragment_count: Mapped[int] = mapped_column(Integer, default=0)  # 生成的片段数量
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关系定义
    fragments: Mapped[list["MetadataKnowledgeFragment"]] = relationship(
        "MetadataKnowledgeFragment", back_populates="document", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index('idx_doc_title', 'title'),
        Index('idx_doc_source_type', 'source_type'),
        Index('idx_doc_created_at', 'created_at'),
        {"mysql_charset": "utf8mb4"},
    )

    def __repr__(self):
        return f"<MetadataKnowledgeDocument(id={self.id}, title='{self.title}', source_type='{self.source_type}')>"


class MetadataKnowledgeFragment(Base):
    """知识片段模型 - 存储LLM生成的知识片段和用户提取的知识"""
    __tablename__ = "metadata_knowledge_fragments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(Integer, ForeignKey("metadata_knowledge_documents.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)  # 知识片段内容（最终版本）
    summary: Mapped[str] = mapped_column(Text, nullable=True)  # 简短摘要
    generation_method: Mapped[str] = mapped_column(String(50), nullable=False)  # 'auto', 'user_extraction', 'manual'
    extraction_theme: Mapped[str] = mapped_column(String(500), nullable=True)  # 提取主题（仅 user_extraction 时有值）
    extraction_prompt: Mapped[str] = mapped_column(Text, nullable=True)  # 提取逻辑描述（仅 user_extraction 时有值）
    is_modified: Mapped[bool] = mapped_column(Boolean, default=False)  # 用户是否修改过
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关系定义
    document: Mapped["MetadataKnowledgeDocument"] = relationship("MetadataKnowledgeDocument", back_populates="fragments")

    __table_args__ = (
        Index('idx_fragment_doc_id', 'document_id'),
        Index('idx_fragment_generation_method', 'generation_method'),
        Index('idx_fragment_created_at', 'created_at'),
        {"mysql_charset": "utf8mb4"},
    )

    def __repr__(self):
        return f"<MetadataKnowledgeFragment(id={self.id}, title='{self.title}', generation_method='{self.generation_method}')>"