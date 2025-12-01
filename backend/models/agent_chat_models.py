"""
聊天会话和历史记录模型
"""
from sqlalchemy import Column, String, Text, DateTime, JSON, ForeignKey, Integer, LargeBinary
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from models.db_base import Base

def generate_uuid():
    return str(uuid.uuid4())

class ChatSession(Base):
    """聊天会话模型"""
    __tablename__ = "agent_chat_sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(100), index=True, nullable=False)
    title = Column(String(255), nullable=True)  # 会话标题
    summary = Column(Text, nullable=True)       # 会话摘要
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

