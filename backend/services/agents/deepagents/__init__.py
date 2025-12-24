"""
DeepAgents 多智能体协作模块

包含:
- DataAnalyserAgent: 数据分析智能体（基于 deepagents 框架）
- QuestionProposerAgent: 问题提出智能体
- ScorerAgent: 评分智能体
- multi_agent_pipeline: 多智能体流水线入口

使用方式:
    # 全自动流水线
    python -m services.agents.deepagents.multi_agent_pipeline

    # 手动指定问题
    python -m services.agents.deepagents.multi_agent_pipeline -q "分析问题"
"""

from services.agents.deepagents.data_analyser_agent import (
    DataAnalyserAgent,
    create_data_analyser_agent,
    create_deep_analyse_service,
)
from services.agents.deepagents.question_proposer_agent import (
    QuestionProposerAgent,
    create_question_proposer_agent,
)
from services.agents.deepagents.scorer_agent import (
    ScorerAgent,
    create_scorer_agent,
)

__all__ = [
    # 数据分析智能体
    "DataAnalyserAgent",
    "create_data_analyser_agent",
    # 问题提出智能体
    "QuestionProposerAgent",
    "create_question_proposer_agent",
    # 评分智能体
    "ScorerAgent",
    "create_scorer_agent",
    "create_deep_analyse_service",
]
