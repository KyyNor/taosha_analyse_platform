"""
DeepAgents 分析追踪数据库模型

记录分析会话和评分信息
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, relationship

from models.db_base import Base


class AnalysisSession(Base):
    """分析会话记录"""
    __tablename__ = "deepagents_analysis_sessions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(String(36), unique=True, nullable=False, index=True, comment="会话唯一标识")

    # 基本信息
    question = Column(Text, nullable=False, comment="分析问题/主题")
    question_source = Column(String(32), default="manual", comment="问题来源: manual/proposer")
    proposer_topic_id = Column(Integer, nullable=True, comment="问题提出智能体的主题ID")

    # 执行信息
    status = Column(String(16), default="pending", comment="状态: pending/running/completed/failed")
    start_time = Column(DateTime, nullable=True, comment="开始时间")
    end_time = Column(DateTime, nullable=True, comment="结束时间")
    duration_seconds = Column(Float, nullable=True, comment="执行耗时(秒)")

    # 输出信息
    report_path = Column(String(512), nullable=True, comment="报告文件路径")
    report_content = Column(Text, nullable=True, comment="报告内容(HTML)")
    llm_output = Column(Text, nullable=True, comment="大模型最终输出")

    # 审计信息
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    # 关系
    scores: Mapped[Optional["AnalysisScore"]] = relationship(
        "AnalysisScore",
        back_populates="session",
        uselist=False,
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<AnalysisSession(session_id='{self.session_id}', question='{self.question[:30]}...', status='{self.status}')>"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "question": self.question,
            "question_source": self.question_source,
            "proposer_topic_id": self.proposer_topic_id,
            "status": self.status,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "report_path": self.report_path,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class AnalysisScore(Base):
    """分析评分记录"""
    __tablename__ = "deepagents_analysis_scores"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(
        String(36),
        ForeignKey("deepagents_analysis_sessions.session_id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
        comment="关联的会话ID"
    )

    # 分析过程评分
    process_score = Column(Integer, nullable=True, comment="分析过程评分(0-100)")
    process_reasons = Column(JSON, nullable=True, comment="过程评分原因列表")
    process_deductions = Column(JSON, nullable=True, comment="过程扣分项")

    # 分析报告评分
    report_score = Column(Integer, nullable=True, comment="分析报告评分(0-100)")
    report_reasons = Column(JSON, nullable=True, comment="报告评分原因列表")
    report_deductions = Column(JSON, nullable=True, comment="报告扣分项")

    # 分析结论评分
    conclusion_score = Column(Integer, nullable=True, comment="分析结论评分(0-100)")
    conclusion_reasons = Column(JSON, nullable=True, comment="结论评分原因列表")
    conclusion_deductions = Column(JSON, nullable=True, comment="结论扣分项")

    # 综合评分
    overall_score = Column(Integer, nullable=True, comment="综合评分(0-100)")

    # 改进建议
    improvement_suggestions = Column(JSON, nullable=True, comment="改进建议列表")

    # 审计
    scored_at = Column(DateTime, default=datetime.now, comment="评分时间")
    scorer_model = Column(String(64), nullable=True, comment="评分使用的模型")

    # 关系
    session: Mapped["AnalysisSession"] = relationship(
        "AnalysisSession",
        back_populates="scores"
    )

    def __repr__(self) -> str:
        return f"<AnalysisScore(session_id='{self.session_id}', overall_score={self.overall_score})>"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "process_score": self.process_score,
            "process_reasons": self.process_reasons,
            "process_deductions": self.process_deductions,
            "report_score": self.report_score,
            "report_reasons": self.report_reasons,
            "report_deductions": self.report_deductions,
            "conclusion_score": self.conclusion_score,
            "conclusion_reasons": self.conclusion_reasons,
            "conclusion_deductions": self.conclusion_deductions,
            "overall_score": self.overall_score,
            "improvement_suggestions": self.improvement_suggestions,
            "scored_at": self.scored_at.isoformat() if self.scored_at else None,
            "scorer_model": self.scorer_model,
        }
