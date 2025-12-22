"""
SQLAlchemy数据模型层
"""

from .db_base import Base, engine, SessionLocal
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
from .training_models import (
    TrainingRecord
)
from .agent_chat_models import (
    ChatSession
)
from .fine_report_models import (
    MetadataFineReport
)

from .fraudhunter import (
    FraudHunterIndicatorTask,
    FraudHunterIndicatorTaskHistory,
    FraudHunterIndicatorDefinition,
    FraudHunterIndicatorHistory,
    FraudHunterModelDefinition,
    FraudHunterModelHistory,
    FraudHunterDryRunExecution,
)

from .deepagents import (
    AnalysisSession,
    AnalysisScore,
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

    # 训练模型
    "TrainingRecord",

    # 聊天/Agent相关
    "ChatSession",
    "ChatMessage",
    "AgentCheckpoint",
    
    # FineReport报表元数据模型
    "MetadataFineReport",

    # FraudHunter模块
    "FraudHunterIndicatorTask",
    "FraudHunterIndicatorTaskHistory",
    "FraudHunterIndicatorDefinition",
    "FraudHunterIndicatorHistory",
    "FraudHunterModelDefinition",
    "FraudHunterModelHistory",
    "FraudHunterDryRunExecution",

    # DeepAgents模块
    "AnalysisSession",
    "AnalysisScore",
]