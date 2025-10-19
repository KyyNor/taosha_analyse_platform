"""
训练数据相关的Repository类
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, asc
from utils.logger import logger

from .base_repository import BaseRepository
from models.training_models import TrainingData, TrainingSession, TrainingMetrics, SQLValidationResult


class TrainingDataRepository(BaseRepository):
    """训练数据Repository"""

    def __init__(self, db: Session):
        super().__init__(TrainingData, db)

    def get_by_category(self, category: str, limit: int = None) -> List[TrainingData]:
        """根据分类获取训练数据"""
        try:
            query = self.db.query(TrainingData).filter(TrainingData.category == category)
            if limit:
                query = query.limit(limit)
            return query.all()
        except Exception as e:
            logger.error(f"获取分类 '{category}' 的训练数据失败: {e}")
            return []

    def get_by_difficulty(self, difficulty: str, limit: int = None) -> List[TrainingData]:
        """根据难度获取训练数据"""
        try:
            query = self.db.query(TrainingData).filter(TrainingData.difficulty == difficulty)
            if limit:
                query = query.limit(limit)
            return query.all()
        except Exception as e:
            logger.error(f"获取难度 '{difficulty}' 的训练数据失败: {e}")
            return []

    def get_verified_data(self, limit: int = None) -> List[TrainingData]:
        """获取已验证的训练数据"""
        try:
            query = self.db.query(TrainingData).filter(TrainingData.is_verified == True)
            if limit:
                query = query.limit(limit)
            return query.all()
        except Exception as e:
            logger.error(f"获取已验证的训练数据失败: {e}")
            return []

    def get_by_quality_threshold(self, min_quality: float = 0.5, limit: int = None) -> List[TrainingData]:
        """获取质量评分高于阈值的训练数据"""
        try:
            query = self.db.query(TrainingData).filter(TrainingData.quality_score >= min_quality)
            if limit:
                query = query.limit(limit)
            return query.all()
        except Exception as e:
            logger.error(f"获取质量评分 >= {min_quality} 的训练数据失败: {e}")
            return []

    def search_by_question(self, keyword: str, limit: int = 10) -> List[TrainingData]:
        """按问题关键字搜索"""
        try:
            return self.db.query(TrainingData).filter(
                TrainingData.question.contains(keyword)
            ).limit(limit).all()
        except Exception as e:
            logger.error(f"搜索问题失败: {e}")
            return []

    def get_most_used(self, limit: int = 10) -> List[TrainingData]:
        """获取使用最频繁的训练数据"""
        try:
            return self.db.query(TrainingData).order_by(
                desc(TrainingData.usage_count)
            ).limit(limit).all()
        except Exception as e:
            logger.error(f"获取最频繁使用的训练数据失败: {e}")
            return []

    def get_statistics(self) -> Dict[str, Any]:
        """获取训练数据统计信息"""
        try:
            total = self.db.query(TrainingData).count()
            verified = self.db.query(TrainingData).filter(TrainingData.is_verified == True).count()
            avg_quality = self.db.query(TrainingData.quality_score).all()

            if avg_quality:
                avg_score = sum(q[0] for q in avg_quality) / len(avg_quality)
            else:
                avg_score = 0.0

            categories = self.db.query(TrainingData.category).distinct().all()
            category_count = {cat[0]: self.db.query(TrainingData).filter(
                TrainingData.category == cat[0]
            ).count() for cat in categories}

            return {
                "total": total,
                "verified": verified,
                "unverified": total - verified,
                "average_quality": avg_score,
                "categories": category_count
            }
        except Exception as e:
            logger.error(f"获取训练数据统计失败: {e}")
            return {}

    def update_usage_stats(self, training_id: int, success: bool = True) -> bool:
        """更新使用统计"""
        try:
            training_data = self.get_by_id(training_id)
            if not training_data:
                return False

            update_data = {"usage_count": training_data.usage_count + 1}
            if success:
                update_data["success_count"] = training_data.success_count + 1

            self.update(training_id, **update_data)
            return True
        except Exception as e:
            logger.error(f"更新使用统计失败: {e}")
            return False


class TrainingSessionRepository(BaseRepository):
    """训练会话Repository"""

    def __init__(self, db: Session):
        super().__init__(TrainingSession, db)

    def get_active_sessions(self) -> List[TrainingSession]:
        """获取正在进行中的训练会话"""
        try:
            return self.db.query(TrainingSession).filter(
                TrainingSession.status.in_(["pending", "running"])
            ).all()
        except Exception as e:
            logger.error(f"获取活跃训练会话失败: {e}")
            return []

    def get_by_status(self, status: str, limit: int = None) -> List[TrainingSession]:
        """根据状态获取训练会话"""
        try:
            query = self.db.query(TrainingSession).filter(TrainingSession.status == status)
            if limit:
                query = query.limit(limit)
            return query.all()
        except Exception as e:
            logger.error(f"获取状态为 '{status}' 的训练会话失败: {e}")
            return []

    def get_recent_sessions(self, days: int = 7, limit: int = 10) -> List[TrainingSession]:
        """获取最近N天的训练会话"""
        try:
            from datetime import datetime, timedelta
            since = datetime.now() - timedelta(days=days)
            return self.db.query(TrainingSession).filter(
                TrainingSession.created_at >= since
            ).order_by(desc(TrainingSession.created_at)).limit(limit).all()
        except Exception as e:
            logger.error(f"获取最近 {days} 天的训练会话失败: {e}")
            return []

    def get_session_summary(self, session_id: int) -> Optional[Dict[str, Any]]:
        """获取训练会话的摘要信息"""
        try:
            session = self.get_by_id(session_id)
            if not session:
                return None

            return {
                "id": session.id,
                "name": session.session_name,
                "status": session.status,
                "total_samples": session.total_samples,
                "success_rate": session.success_rate,
                "training_time": f"{session.training_time_seconds:.2f}s",
                "average_confidence": session.average_confidence,
                "created_at": session.created_at.isoformat(),
                "completed_at": session.completed_at.isoformat() if session.completed_at else None
            }
        except Exception as e:
            logger.error(f"获取会话 {session_id} 摘要失败: {e}")
            return None

    def update_session_progress(self, session_id: int, total: int = None, successful: int = None,
                               failed: int = None, status: str = None) -> bool:
        """更新会话进度"""
        try:
            update_data = {}
            if total is not None:
                update_data["total_samples"] = total
            if successful is not None:
                update_data["successful_samples"] = successful
            if failed is not None:
                update_data["failed_samples"] = failed
            if status is not None:
                update_data["status"] = status
                if status == "running":
                    from datetime import datetime
                    update_data["started_at"] = datetime.now()

            if update_data:
                self.update(session_id, **update_data)
            return True
        except Exception as e:
            logger.error(f"更新会话进度失败: {e}")
            return False

    def complete_session(self, session_id: int, success_rate: float = 0.0,
                        avg_confidence: float = 0.0, training_time: float = 0.0) -> bool:
        """标记训练会话为完成"""
        try:
            from datetime import datetime
            self.update(
                session_id,
                status="completed",
                success_rate=success_rate,
                average_confidence=avg_confidence,
                training_time_seconds=training_time,
                completed_at=datetime.now()
            )
            return True
        except Exception as e:
            logger.error(f"完成会话失败: {e}")
            return False


class TrainingMetricsRepository(BaseRepository):
    """训练指标Repository"""

    def __init__(self, db: Session):
        super().__init__(TrainingMetrics, db)

    def get_by_session(self, session_id: int) -> List[TrainingMetrics]:
        """获取某个训练会话的所有指标"""
        try:
            return self.db.query(TrainingMetrics).filter(
                TrainingMetrics.session_id == session_id
            ).all()
        except Exception as e:
            logger.error(f"获取会话 {session_id} 的指标失败: {e}")
            return []

    def get_by_metric_type(self, metric_type: str) -> List[TrainingMetrics]:
        """按指标类型获取"""
        try:
            return self.db.query(TrainingMetrics).filter(
                TrainingMetrics.metric_type == metric_type
            ).all()
        except Exception as e:
            logger.error(f"获取类型为 '{metric_type}' 的指标失败: {e}")
            return []

    def add_metric(self, session_id: int, metric_name: str, metric_value: float,
                   metric_type: str = "performance", description: str = "") -> bool:
        """添加训练指标"""
        try:
            self.create(
                session_id=session_id,
                metric_name=metric_name,
                metric_value=metric_value,
                metric_type=metric_type,
                description=description
            )
            return True
        except Exception as e:
            logger.error(f"添加指标失败: {e}")
            return False


class SQLValidationResultRepository(BaseRepository):
    """SQL验证结果Repository"""

    def __init__(self, db: Session):
        super().__init__(SQLValidationResult, db)

    def get_by_training_data(self, training_data_id: int) -> List[SQLValidationResult]:
        """获取某条训练数据的所有验证结果"""
        try:
            return self.db.query(SQLValidationResult).filter(
                SQLValidationResult.training_data_id == training_data_id
            ).all()
        except Exception as e:
            logger.error(f"获取训练数据 {training_data_id} 的验证结果失败: {e}")
            return []

    def get_by_execution_status(self, status: str, limit: int = None) -> List[SQLValidationResult]:
        """根据执行状态获取结果"""
        try:
            query = self.db.query(SQLValidationResult).filter(
                SQLValidationResult.execution_status == status
            )
            if limit:
                query = query.limit(limit)
            return query.all()
        except Exception as e:
            logger.error(f"获取执行状态为 '{status}' 的结果失败: {e}")
            return []

    def get_failed_validations(self, limit: int = 10) -> List[SQLValidationResult]:
        """获取验证失败的结果"""
        try:
            return self.db.query(SQLValidationResult).filter(
                SQLValidationResult.is_valid == False
            ).order_by(desc(SQLValidationResult.created_at)).limit(limit).all()
        except Exception as e:
            logger.error(f"获取失败的验证结果失败: {e}")
            return []

    def get_validation_statistics(self) -> Dict[str, Any]:
        """获取验证统计信息"""
        try:
            total = self.db.query(SQLValidationResult).count()
            valid = self.db.query(SQLValidationResult).filter(
                SQLValidationResult.is_valid == True
            ).count()
            success_status = self.db.query(SQLValidationResult).filter(
                SQLValidationResult.execution_status == "success"
            ).count()

            return {
                "total": total,
                "valid": valid,
                "invalid": total - valid,
                "success_rate": (success_status / total * 100) if total > 0 else 0,
                "validation_rate": (valid / total * 100) if total > 0 else 0
            }
        except Exception as e:
            logger.error(f"获取验证统计失败: {e}")
            return {}
