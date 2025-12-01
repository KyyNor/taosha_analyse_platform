"""
聊天记录仓储类
"""
from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy import desc, asc
from sqlalchemy.orm import Session

from models.db_base import get_db_session
from models.agent_chat_models import ChatSession

class ChatRepository:
    """聊天记录仓储类"""

    def create_session(self, user_id: str, session_id: str, title: str = None) -> ChatSession:
        """创建或获取会话"""
        with get_db_session() as db:
            session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
            if not session:
                session = ChatSession(
                    id=session_id,
                    user_id=user_id,
                    title=title or "新会话"
                )
                db.add(session)
                db.commit()
                db.refresh(session)
            return session

    def update_session_title(self, session_id: str, title: str):
        """更新会话标题"""
        with get_db_session() as db:
            session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
            if session:
                session.title = title
                session.updated_at = datetime.now()
                db.add(session)

    def get_user_sessions(self, user_id: str, limit: int = 20) -> List[ChatSession]:
        """获取用户的会话列表"""
        with get_db_session() as db:
            sessions = db.query(ChatSession)\
                .filter(ChatSession.user_id == user_id)\
                .order_by(desc(ChatSession.updated_at))\
                .limit(limit)\
                .all()
            return sessions

    def delete_session(self, session_id: str, user_id: str) -> bool:
        """删除会话"""
        with get_db_session() as db:
            session = db.query(ChatSession)\
                .filter(ChatSession.id == session_id, ChatSession.user_id == user_id)\
                .first()
            if session:
                db.delete(session)
                return True
            return False
