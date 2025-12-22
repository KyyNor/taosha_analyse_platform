"""
DeepAgents 分析追踪 Repository

提供分析会话和评分的数据访问层
"""
from datetime import datetime
from typing import Dict, List, Optional, Any

from sqlalchemy import desc, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from models.deepagents import AnalysisSession, AnalysisScore
from repositories.base_repository import BaseRepository
from utils.logger import logger


class AnalysisSessionRepository(BaseRepository[AnalysisSession]):
    """分析会话 Repository"""

    def __init__(self, db: Session):
        super().__init__(AnalysisSession, db)

    def get_by_session_id(self, session_id: str) -> Optional[AnalysisSession]:
        """根据 session_id 获取会话"""
        try:
            return self.db.query(AnalysisSession).filter(
                AnalysisSession.session_id == session_id
            ).first()
        except SQLAlchemyError as e:
            logger.error(f"获取会话失败: {e}")
            raise

    def get_recent_sessions(self, limit: int = 20) -> List[AnalysisSession]:
        """获取最近的会话列表"""
        try:
            return self.db.query(AnalysisSession).order_by(
                desc(AnalysisSession.created_at)
            ).limit(limit).all()
        except SQLAlchemyError as e:
            logger.error(f"获取最近会话失败: {e}")
            raise

    def get_sessions_with_scores(self, min_score: int = 0) -> List[AnalysisSession]:
        """获取带有评分的会话列表"""
        try:
            query = self.db.query(AnalysisSession).join(
                AnalysisScore,
                AnalysisSession.session_id == AnalysisScore.session_id
            )
            if min_score > 0:
                query = query.filter(AnalysisScore.overall_score >= min_score)
            return query.order_by(desc(AnalysisSession.created_at)).all()
        except SQLAlchemyError as e:
            logger.error(f"获取带评分会话失败: {e}")
            raise

    def search_by_question(self, keyword: str) -> List[AnalysisSession]:
        """根据问题关键词搜索会话"""
        try:
            return self.db.query(AnalysisSession).filter(
                AnalysisSession.question.like(f"%{keyword}%")
            ).order_by(desc(AnalysisSession.created_at)).all()
        except SQLAlchemyError as e:
            logger.error(f"搜索会话失败: {e}")
            raise

    def get_completed_sessions(self, limit: int = 10) -> List[AnalysisSession]:
        """获取已完成的会话列表（用于问题提出智能体）"""
        try:
            return self.db.query(AnalysisSession).filter(
                AnalysisSession.status == "completed"
            ).order_by(desc(AnalysisSession.created_at)).limit(limit).all()
        except SQLAlchemyError as e:
            logger.error(f"获取已完成会话失败: {e}")
            raise

    def update_status(
        self,
        session_id: str,
        status: str,
        end_time: Optional[datetime] = None,
        duration_seconds: Optional[float] = None
    ) -> Optional[AnalysisSession]:
        """更新会话状态"""
        try:
            session = self.get_by_session_id(session_id)
            if session:
                session.status = status
                if end_time:
                    session.end_time = end_time
                if duration_seconds:
                    session.duration_seconds = duration_seconds
                self.db.commit()
                self.db.refresh(session)
                logger.info(f"更新会话状态成功: {session_id} -> {status}")
            return session
        except SQLAlchemyError as e:
            logger.error(f"更新会话状态失败: {e}")
            raise

    def save_report(
        self,
        session_id: str,
        report_path: str,
        report_content: str,
        llm_output: str
    ) -> Optional[AnalysisSession]:
        """保存分析报告"""
        try:
            session = self.get_by_session_id(session_id)
            if session:
                session.report_path = report_path
                session.report_content = report_content
                session.llm_output = llm_output
                self.db.commit()
                self.db.refresh(session)
                logger.info(f"保存会话报告成功: {session_id}")
            return session
        except SQLAlchemyError as e:
            logger.error(f"保存会话报告失败: {e}")
            raise

    def get_history_summary(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取历史摘要（用于问题提出智能体）"""
        try:
            sessions = self.get_completed_sessions(limit)
            summaries = []
            for session in sessions:
                summary = {
                    "session_id": session.session_id,
                    "question": session.question,
                    "question_source": session.question_source,
                    "duration_seconds": session.duration_seconds,
                    "created_at": session.created_at.isoformat() if session.created_at else None,
                }
                # 如果有评分，添加评分信息
                if session.scores:
                    summary["overall_score"] = session.scores.overall_score
                summaries.append(summary)
            return summaries
        except SQLAlchemyError as e:
            logger.error(f"获取历史摘要失败: {e}")
            raise


class AnalysisScoreRepository(BaseRepository[AnalysisScore]):
    """分析评分 Repository"""

    def __init__(self, db: Session):
        super().__init__(AnalysisScore, db)

    def get_by_session_id(self, session_id: str) -> Optional[AnalysisScore]:
        """根据 session_id 获取评分"""
        try:
            return self.db.query(AnalysisScore).filter(
                AnalysisScore.session_id == session_id
            ).first()
        except SQLAlchemyError as e:
            logger.error(f"获取评分失败: {e}")
            raise

    def get_average_scores(self) -> Dict[str, float]:
        """获取平均评分"""
        try:
            result = self.db.query(
                func.avg(AnalysisScore.process_score).label("avg_process"),
                func.avg(AnalysisScore.report_score).label("avg_report"),
                func.avg(AnalysisScore.conclusion_score).label("avg_conclusion"),
                func.avg(AnalysisScore.overall_score).label("avg_overall"),
            ).first()

            return {
                "avg_process_score": float(result.avg_process or 0),
                "avg_report_score": float(result.avg_report or 0),
                "avg_conclusion_score": float(result.avg_conclusion or 0),
                "avg_overall_score": float(result.avg_overall or 0),
            }
        except SQLAlchemyError as e:
            logger.error(f"获取平均评分失败: {e}")
            raise

    def get_low_score_sessions(self, threshold: int = 60) -> List[AnalysisScore]:
        """获取低分会话列表"""
        try:
            return self.db.query(AnalysisScore).filter(
                AnalysisScore.overall_score < threshold
            ).order_by(AnalysisScore.overall_score).all()
        except SQLAlchemyError as e:
            logger.error(f"获取低分会话失败: {e}")
            raise

    def save_scores(
        self,
        session_id: str,
        process_score: int,
        process_reasons: List[str],
        process_deductions: List[str],
        report_score: int,
        report_reasons: List[str],
        report_deductions: List[str],
        conclusion_score: int,
        conclusion_reasons: List[str],
        conclusion_deductions: List[str],
        overall_score: int,
        improvement_suggestions: List[Dict[str, Any]],
        scorer_model: str = None
    ) -> AnalysisScore:
        """保存评分结果"""
        try:
            # 检查是否已存在评分
            existing = self.get_by_session_id(session_id)
            if existing:
                # 更新现有评分
                existing.process_score = process_score
                existing.process_reasons = process_reasons
                existing.process_deductions = process_deductions
                existing.report_score = report_score
                existing.report_reasons = report_reasons
                existing.report_deductions = report_deductions
                existing.conclusion_score = conclusion_score
                existing.conclusion_reasons = conclusion_reasons
                existing.conclusion_deductions = conclusion_deductions
                existing.overall_score = overall_score
                existing.improvement_suggestions = improvement_suggestions
                existing.scorer_model = scorer_model
                existing.scored_at = datetime.now()
                self.db.commit()
                self.db.refresh(existing)
                logger.info(f"更新评分成功: {session_id}")
                return existing
            else:
                # 创建新评分
                score = AnalysisScore(
                    session_id=session_id,
                    process_score=process_score,
                    process_reasons=process_reasons,
                    process_deductions=process_deductions,
                    report_score=report_score,
                    report_reasons=report_reasons,
                    report_deductions=report_deductions,
                    conclusion_score=conclusion_score,
                    conclusion_reasons=conclusion_reasons,
                    conclusion_deductions=conclusion_deductions,
                    overall_score=overall_score,
                    improvement_suggestions=improvement_suggestions,
                    scorer_model=scorer_model,
                )
                self.db.add(score)
                self.db.commit()
                self.db.refresh(score)
                logger.info(f"保存评分成功: {session_id}")
                return score
        except SQLAlchemyError as e:
            logger.error(f"保存评分失败: {e}")
            raise
