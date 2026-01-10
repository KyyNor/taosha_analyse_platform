"""
权限管理相关的SQLAlchemy模型
"""

from sqlalchemy import Column, String, Text, DateTime, JSON, ForeignKey, Enum, UniqueConstraint, Index, Boolean, Integer
from sqlalchemy.orm import relationship, Mapped, mapped_column, backref
from datetime import datetime
import enum
from typing import Optional
from .db_base import Base


class EntityType(enum.Enum):
    """实体类型枚举"""
    DEPARTMENT = "department"
    ROLE = "role"


class SystemEntity(Base):
    """系统实体模型 - 合并部门和角色"""
    __tablename__ = "system_entities"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False, comment="实体编码，用于与外部系统对接")
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="实体名称")
    type: Mapped[EntityType] = mapped_column(Enum(EntityType), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否为管理员实体")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关系定义
    permissions: Mapped[list["SystemPermission"]] = relationship(
        "SystemPermission", back_populates="entity", cascade="all, delete-orphan"
    )

    # 表约束
    __table_args__ = (
        UniqueConstraint('code', 'type', name='unique_code_type'),
        Index('idx_code', 'code'),
        Index('idx_type', 'type'),
        {"mysql_charset": "utf8mb4"},
    )

    def __repr__(self):
        return f"<SystemEntity(id='{self.id}', code='{self.code}', name='{self.name}', type='{self.type.value}')>"


class SystemPage(Base):
    """系统页面模型 - 支持层级结构"""
    __tablename__ = "system_pages"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    path: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    # 层级支持字段
    parent_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        ForeignKey("system_pages.id", ondelete="CASCADE"),
        nullable=True,
        comment="父页面ID，根页面为NULL"
    )
    level: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="层级深度，根页面为0"
    )
    path_hash: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        default="",
        comment="层级路径哈希"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="同级排序顺序"
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 自引用关系 - 父子关系
    children: Mapped[list["SystemPage"]] = relationship(
        "SystemPage",
        backref=backref("parent", remote_side=[id]),
        cascade="all, delete-orphan"
    )

    # 表约束
    __table_args__ = (
        Index('idx_parent_id', 'parent_id'),
        Index('idx_level', 'level'),
        Index('idx_path_hash', 'path_hash'),
        {"mysql_charset": "utf8mb4"},
    )

    def __repr__(self):
        return f"<SystemPage(id='{self.id}', path='{self.path}', name='{self.name}', level={self.level})>"


class SystemPermission(Base):
    """系统权限模型 - 合并部门权限和角色权限"""
    __tablename__ = "system_permissions"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    entity_id: Mapped[str] = mapped_column(String(50), ForeignKey("system_entities.id"), nullable=False, comment="实体ID（部门或角色）")
    page_id: Mapped[str] = mapped_column(String(50), ForeignKey("system_pages.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # 关系定义
    entity: Mapped["SystemEntity"] = relationship("SystemEntity", back_populates="permissions")
    page: Mapped["SystemPage"] = relationship("SystemPage")

    # 表约束
    __table_args__ = (
        UniqueConstraint('entity_id', 'page_id', name='unique_entity_page'),
        {"mysql_charset": "utf8mb4"},
    )

    def __repr__(self):
        return f"<SystemPermission(id='{self.id}', entity_id='{self.entity_id}', page_id='{self.page_id}')>"


class SystemLoginRecord(Base):
    """系统登录记录模型"""
    __tablename__ = "system_login_records"

    user_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    user_name: Mapped[str] = mapped_column(String(100), nullable=False)
    branch_no: Mapped[str] = mapped_column(String(100), nullable=False, comment="部门编号")
    branch_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="部门名称")
    role_id_list: Mapped[dict] = mapped_column(JSON, nullable=False, comment="角色ID列表")
    role_name_list: Mapped[dict] = mapped_column(JSON, nullable=False, comment="角色名称列表（仅包含在entity中存在的角色）")
    last_login_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 表约束
    __table_args__ = (
        {"mysql_charset": "utf8mb4"},
    )

    def __repr__(self):
        return f"<SystemLoginRecord(user_id='{self.user_id}', user_name='{self.user_name}', last_login_time='{self.last_login_time}')>"