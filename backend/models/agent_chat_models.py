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
    
    # 关联消息
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

class ChatMessage(Base):
    """聊天消息模型"""
    __tablename__ = "agent_chat_messages"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(36), ForeignKey("agent_chat_sessions.id"), index=True, nullable=False)
    
    role = Column(String(50), nullable=False)  # user, assistant, system, tool
    type = Column(String(50), default="text")  # text, json, chart, etc.
    content = Column(Text, nullable=True)      # 消息内容 (JSON string if complex)
    
    # 额外元数据 (如 tool_call_id, trace_id, execution_time 等)
    meta_info = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.now)
    
    session = relationship("ChatSession", back_populates="messages")

class AgentCheckpoint(Base):
    """LangGraph Agent 检查点模型 (用于状态恢复)"""
    __tablename__ = "agent_checkpoints"

    # 复合主键：thread_id + checkpoint_ns + checkpoint_id
    thread_id = Column(String(255), primary_key=True) 
    checkpoint_ns = Column(String(255), primary_key=True, default="") 
    checkpoint_id = Column(String(255), primary_key=True) 
    
    parent_checkpoint_id = Column(String(255), nullable=True)
    
    checkpoint = Column(LargeBinary, nullable=False) # 序列化的 Checkpoint 数据 (msgpack/pickle)
    metadata_ = Column(JSON, nullable=True) # Checkpoint 元数据
    
    created_at = Column(DateTime, default=datetime.now)
