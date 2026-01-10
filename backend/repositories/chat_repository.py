"""
聊天记录仓储类
"""
from typing import List, Dict, Optional
from datetime import datetime
from contextlib import contextmanager
from sqlalchemy import desc, asc
from sqlalchemy.orm import Session

from models.db_base import get_db_session
from models.agent_chat_models import ChatSession

class ChatRepository:
    """聊天记录仓储类"""

    def __init__(self, db: Session = None):
        self.db = db

    @contextmanager
    def _get_db(self):
        if self.db:
            yield self.db
        else:
            with get_db_session() as db:
                yield db

    def create_session(self, user_id: str, session_id: str, title: str = None) -> tuple[ChatSession, bool]:
        """创建或获取会话
        
        Returns:
            tuple[ChatSession, bool]: (会话对象, 是否为新创建)
        """
        with self._get_db() as db:
            session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
            is_new = False
            if not session:
                session = ChatSession(
                    id=session_id,
                    user_id=user_id,
                    title=title or "新会话"
                )
                db.add(session)
                db.commit()
                db.refresh(session)
                is_new = True
            return session, is_new

    def update_session_title(self, session_id: str, title: str):
        """更新会话标题"""
        with self._get_db() as db:
            session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
            if session:
                session.title = title
                session.updated_at = datetime.now()
                db.add(session)
                db.commit()

    def get_user_sessions(self, user_id: str, limit: int = 20) -> List[ChatSession]:
        """获取用户的会话列表"""
        with self._get_db() as db:
            sessions = db.query(ChatSession)\
                .filter(ChatSession.user_id == user_id)\
                .order_by(desc(ChatSession.updated_at))\
                .limit(limit)\
                .all()
            return sessions

    def delete_session(self, session_id: str, user_id: str) -> bool:
        """删除会话"""
        with self._get_db() as db:
            session = db.query(ChatSession)\
                .filter(ChatSession.id == session_id, ChatSession.user_id == user_id)\
                .first()
            if session:
                db.delete(session)
                db.commit()
                return True
            return False