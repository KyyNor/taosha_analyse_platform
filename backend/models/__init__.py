"""
SQLAlchemy数据模型层
"""

from .base import Base, engine, SessionLocal
from .metadata_models import (
    MetadataTable, MetadataColumn
)
from .glossary_models import (
    GlossaryTerm, PromptTemplate
)
from .relation_models import (
    RelationFieldConfig
)
from .tracking_models import (
    NlQuerySession, NlQueryStep, UserFeedback
)
from .theme_models import (
    DataTheme, ThemeTableRelation
)

__all__ = [
    # 基础配置
    "Base",
    "engine",
    "SessionLocal",

    # 元数据模型
    "MetadataTable",
    "MetadataColumn",

    # 术语表模型
    "GlossaryTerm",
    "PromptTemplate",

    # 关联配置模型
    "RelationFieldConfig",

    # 操作追踪模型
    "NlQuerySession",
    "NlQueryStep",
    "UserFeedback",

    # 主题模型
    "DataTheme",
    "ThemeTableRelation",
]