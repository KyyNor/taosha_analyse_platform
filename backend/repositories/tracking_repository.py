"""
操作追踪相关的Repository
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import joinedload
from sqlalchemy import and_, or_, desc
from utils.logger import logger
from models.db_base import get_detached_session
from .base_repository import BaseRepository
from models.tracking_models import NlQuerySession, NlQueryStep, UserFeedback


class NlQuerySessionRepository(BaseRepository[NlQuerySession]):
    """NL查询会话Repository"""

    def __init__(self):
        super().__init__(NlQuerySession)

    def create(self, **kwargs) -> NlQuerySession:
        """
        创建新记录（重写以处理task_id作为主键）

        Args:
            **kwargs: 模型字段参数

        Returns:
            创建的模型实例
        """
        try:
            with get_detached_session() as db:
                instance = self.model_class(**kwargs)
                db.add(instance)
                db.flush()  # 确保获取到主键值
                db.refresh(instance)  # 刷新实例，获取数据库生成的值
                # 将实例状态设置为持久化，避免会话关闭后访问出错
                db.expunge(instance)  # 从会话中分离实例
                logger.info(f"创建 {self.model_class.__name__} 记录成功: task_id={instance.task_id}")
                return instance
        except Exception as e:
            logger.error(f"创建 {self.model_class.__name__} 记录失败: {e}")
            raise

    def get_by_task_id(self, task_id: str) -> Optional[NlQuerySession]:
        """根据任务ID获取会话"""
        try:
            with get_detached_session() as db:
                return db.query(NlQuerySession).filter(NlQuerySession.task_id == task_id).first()
        except Exception as e:
            logger.error(f"根据任务ID获取会话失败: {e}")
            raise

    def get_by_operator(self, operator: str) -> List[NlQuerySession]:
        """根据操作人获取会话列表"""
        try:
            with get_detached_session() as db:
                return db.query(NlQuerySession)\
                         .filter(NlQuerySession.operator == operator)\
                         .order_by(desc(NlQuerySession.created_at))\
                         .all()
        except Exception as e:
            logger.error(f"根据操作人获取会话失败: {e}")
            raise

    def get_by_status(self, status: str) -> List[NlQuerySession]:
        """根据状态获取会话列表"""
        try:
            with get_detached_session() as db:
                return db.query(NlQuerySession)\
                         .filter(NlQuerySession.status == status)\
                         .order_by(desc(NlQuerySession.created_at))\
                         .all()
        except Exception as e:
            logger.error(f"根据状态获取会话失败: {e}")
            raise

    def get_with_steps(self, task_id: str) -> Optional[NlQuerySession]:
        """获取会话及其步骤"""
        try:
            with get_detached_session() as db:
                return db.query(NlQuerySession)\
                         .options(joinedload(NlQuerySession.steps))\
                         .filter(NlQuerySession.task_id == task_id)\
                         .first()
        except Exception as e:
            logger.error(f"获取会话及其步骤失败: {e}")
            raise

    def get_paginated_by_operator(self, operator: str, page: int = 1, page_size: int = 20,
                                  status: str = None) -> Dict[str, Any]:
        """分页获取操作人的会话"""
        try:
            with get_detached_session() as db:
                query = db.query(NlQuerySession).filter(NlQuerySession.operator == operator)

                if status:
                    query = query.filter(NlQuerySession.status == status)

                # 计算总数
                total = query.count()

                # 应用分页
                offset = (page - 1) * page_size
                sessions = query.order_by(desc(NlQuerySession.created_at))\
                              .offset(offset)\
                              .limit(page_size)\
                              .all()

                return {
                    'items': sessions,
                    'total': total,
                    'page': page,
                    'page_size': page_size,
                    'total_pages': (total + page_size - 1) // page_size
                }
        except Exception as e:
            logger.error(f"分页获取会话失败: {e}")
            raise

    def get_recent_sessions(self, limit: int = 10) -> List[NlQuerySession]:
        """获取最近的会话"""
        try:
            with get_detached_session() as db:
                return db.query(NlQuerySession)\
                         .order_by(desc(NlQuerySession.created_at))\
                         .limit(limit)\
                         .all()
        except Exception as e:
            logger.error(f"获取最近会话失败: {e}")
            raise

    def search_sessions(self, query: str) -> List[NlQuerySession]:
        """搜索会话（按用户输入或SQL查询）"""
        try:
            with get_detached_session() as db:
                return db.query(NlQuerySession)\
                         .filter(
                             or_(
                                 NlQuerySession.user_input.contains(query),
                                 NlQuerySession.sql_query.contains(query)
                             )
                         )\
                         .order_by(desc(NlQuerySession.created_at))\
                         .all()
        except Exception as e:
            logger.error(f"搜索会话失败: {e}")
            raise

    def update_by_task_id(self, task_id: str, **kwargs) -> bool:
        """根据task_id更新会话"""
        try:
            with get_detached_session() as db:
                session = db.query(NlQuerySession)\
                            .filter(NlQuerySession.task_id == task_id)\
                            .first()
                if session:
                    for key, value in kwargs.items():
                        if hasattr(session, key):
                            setattr(session, key, value)
                    logger.info(f"更新 {self.model_class.__name__} 记录成功: task_id={task_id}")
                    return True
                return False
        except Exception as e:
            logger.error(f"更新会话失败: {e}")
            raise

    def update_status(self, task_id: str, status: str) -> bool:
        """更新会话状态"""
        return self.update_by_task_id(task_id, status=status)



class NlQueryStepRepository(BaseRepository[NlQueryStep]):
    """NL查询步骤Repository"""

    def __init__(self):
        super().__init__(NlQueryStep)

    def get_by_task_id(self, task_id: str) -> List[NlQueryStep]:
        """根据任务ID获取所有步骤"""
        try:
            with get_detached_session() as db:
                return db.query(NlQueryStep)\
                         .filter(NlQueryStep.task_id == task_id)\
                         .order_by(NlQueryStep.created_at)\
                         .all()
        except Exception as e:
            logger.error(f"根据任务ID获取步骤失败: {e}")
            raise

    def get_by_task_id_and_step(self, task_id: str, step: str) -> Optional[NlQueryStep]:
        """根据任务ID和步骤名获取步骤"""
        try:
            with get_detached_session() as db:
                return db.query(NlQueryStep)\
                         .filter(
                             and_(
                                 NlQueryStep.task_id == task_id,
                                 NlQueryStep.step == step
                             )
                         )\
                         .first()
        except Exception as e:
            logger.error(f"根据任务ID和步骤名获取步骤失败: {e}")
            raise

    def get_successful_steps(self, task_id: str) -> List[NlQueryStep]:
        """获取成功的步骤"""
        try:
            with get_detached_session() as db:
                return db.query(NlQueryStep)\
                         .filter(
                             and_(
                                 NlQueryStep.task_id == task_id,
                                 NlQueryStep.success == 1
                             )
                         )\
                         .order_by(NlQueryStep.created_at)\
                         .all()
        except Exception as e:
            logger.error(f"获取成功步骤失败: {e}")
            raise

    def get_failed_steps(self, task_id: str) -> List[NlQueryStep]:
        """获取失败的步骤"""
        try:
            with get_detached_session() as db:
                return db.query(NlQueryStep)\
                         .filter(
                             and_(
                                 NlQueryStep.task_id == task_id,
                                 NlQueryStep.success == 0
                             )
                         )\
                         .order_by(NlQueryStep.created_at)\
                         .all()
        except Exception as e:
            logger.error(f"获取失败步骤失败: {e}")
            raise



class UserFeedbackRepository(BaseRepository[UserFeedback]):
    """用户反馈Repository"""

    def __init__(self):
        super().__init__(UserFeedback)

    def get_by_session_id(self, session_id: str) -> List[UserFeedback]:
        """根据会话ID获取反馈"""
        try:
            with get_detached_session() as db:
                return db.query(UserFeedback)\
                         .filter(UserFeedback.session_id == session_id)\
                         .order_by(UserFeedback.feedback_time)\
                         .all()
        except Exception as e:
            logger.error(f"根据会话ID获取反馈失败: {e}")
            raise

    def get_by_sentiment(self, sentiment: str) -> List[UserFeedback]:
        """根据情感获取反馈"""
        try:
            with get_detached_session() as db:
                return db.query(UserFeedback)\
                         .filter(UserFeedback.feedback_sentiment == sentiment)\
                         .order_by(desc(UserFeedback.feedback_time))\
                         .all()
        except Exception as e:
            logger.error(f"根据情感获取反馈失败: {e}")
            raise

    def get_by_user(self, user: str) -> List[UserFeedback]:
        """根据用户获取反馈"""
        try:
            with get_detached_session() as db:
                return db.query(UserFeedback)\
                         .filter(UserFeedback.feedback_user == user)\
                         .order_by(desc(UserFeedback.feedback_time))\
                         .all()
        except Exception as e:
            logger.error(f"根据用户获取反馈失败: {e}")
            raise

    def get_db_session(self):
        """获取数据库会话"""
        from models.db_base import get_db_session
        return get_db_session()