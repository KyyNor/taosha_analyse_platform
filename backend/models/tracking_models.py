"""
操作追踪相关的SQLAlchemy模型
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime
from .db_base import Base


class NlQuerySession(Base):
    """NL查询会话记录模型"""
    __tablename__ = "nlquery_sessions"

    task_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    user_input: Mapped[str] = mapped_column(Text, nullable=False)
    operator: Mapped[str] = mapped_column(String(100), default="", index=True)
    flow_type: Mapped[str] = mapped_column(String(50), default="fast", index=True)  # fast, thorough
    status: Mapped[str] = mapped_column(String(50), default="running", index=True)  # running, success, failed, completed
    current_step: Mapped[str] = mapped_column(String(255), default="初始化")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    task_context: Mapped[str] = mapped_column(Text, nullable=True)
    sql_query: Mapped[str] = mapped_column(Text, nullable=True)
    execution_result: Mapped[str] = mapped_column(Text, nullable=True)  # JSON格式
    clear_check_details: Mapped[str] = mapped_column(Text, nullable=True)  # JSON格式
    is_clear: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=5)

    # 关系定义
    steps: Mapped[list["NlQueryStep"]] = relationship(
        "NlQueryStep", back_populates="session", cascade="all, delete-orphan"
    )
    feedbacks: Mapped[list["UserFeedback"]] = relationship(
        "UserFeedback", back_populates="session", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<NlQuerySession(task_id='{self.task_id}', status='{self.status}')>"


class NlQueryStep(Base):
    """NL查询步骤详情模型"""
    __tablename__ = "nlquery_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(255), ForeignKey("nlquery_sessions.task_id"), nullable=False, index=True)
    step: Mapped[str] = mapped_column(String(255), nullable=False)
    input_data: Mapped[str] = mapped_column(Text, nullable=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=True)
    model_output: Mapped[str] = mapped_column(Text, nullable=True)
    success: Mapped[int] = mapped_column(Integer, default=1)  # 1=成功，0=失败
    error: Mapped[str] = mapped_column(Text, nullable=True)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # 关系定义
    session: Mapped["NlQuerySession"] = relationship("NlQuerySession", back_populates="steps")

    def __repr__(self):
        return f"<NlQueryStep(id={self.id}, task_id='{self.task_id}', step='{self.step}')>"


class UserFeedback(Base):
    """用户反馈模型"""
    __tablename__ = "nlquery_user_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    feedback_type: Mapped[str] = mapped_column(String(50), nullable=False)
    session_id: Mapped[str] = mapped_column(String(255), ForeignKey("nlquery_sessions.task_id"), nullable=False, index=True)
    step_sequence: Mapped[int] = mapped_column(Integer, nullable=True)
    feedback_sentiment: Mapped[str] = mapped_column(String(50), nullable=False)
    feedback_content: Mapped[str] = mapped_column(Text, nullable=False)
    feedback_user: Mapped[str] = mapped_column(String(100), default="")
    feedback_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # 关系定义
    session: Mapped["NlQuerySession"] = relationship("NlQuerySession", back_populates="feedbacks")

    def __repr__(self):
        return f"<UserFeedback(id={self.id}, session_id='{self.session_id}', sentiment='{self.feedback_sentiment}')>"