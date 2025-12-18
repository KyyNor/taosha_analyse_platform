"""
DeepAgents 数据分析智能体模块
用于 python -m 方式运行

使用方式:
    python -m backend.services.agents.deepagents "分析问题"
    python -m backend.services.agents.deepagents --interactive
"""

from services.agents.deep_analyse_agent_service import (
    DeepAnalyseAgentService,
    create_deep_analyse_service,
)

__all__ = [
    "DeepAnalyseAgentService",
    "create_deep_analyse_service",
]
