"""
操作追踪服务 - 追踪LangGraph和大模型调用的详细信息
"""

import uuid
import json
import threading
from datetime import datetime
from typing import Dict, Any, Optional
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from utils.logger import logger

from utils.db_utils import get_database_manager


@dataclass
class TokenUsage:
    """Token使用统计"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    
    def to_dict(self) -> Dict[str, int]:
        return asdict(self)


@dataclass
class OperationStep:
    """操作步骤数据"""
    session_id: str
    step_sequence: int
    step_name: str
    input_data: str = ""
    call_method: str = ""
    output_data: str = ""
    generated_sql: str = ""
    error_message: str = ""
    success: bool = True
    duration: int = 0
    token_usage: Optional[TokenUsage] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.token_usage is None:
            self.token_usage = TokenUsage()


class OperationTracker:
    """操作追踪器 - 线程安全的单例"""
    
    _instance = None
    _lock = threading.Lock()
    _local = threading.local()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.db_manager = get_database_manager()
            self.initialized = True
    
    @property
    def current_session(self) -> Optional[str]:
        """获取当前线程的session_id"""
        return getattr(self._local, 'session_id', None)
    
    @current_session.setter
    def current_session(self, session_id: str):
        """设置当前线程的session_id"""
        self._local.session_id = session_id
    
    @property
    def current_step_sequence(self) -> int:
        """获取当前线程的步骤序号"""
        return getattr(self._local, 'step_sequence', 0)
    
    @current_step_sequence.setter
    def current_step_sequence(self, sequence: int):
        """设置当前线程的步骤序号"""
        self._local.step_sequence = sequence
    
    def start_session(self, operation_type: str, operator: str = None) -> str:
        """开始一个新的操作会话"""
        session_id = str(uuid.uuid4())
        self.current_session = session_id
        self.current_step_sequence = 0
        
        self.db_manager.execute_query("""
            INSERT INTO operation_sessions 
            (session_id, operation_type, operator, start_time, status)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, operation_type, operator, datetime.now().isoformat(), 'running'))
        
        logger.info(f"Started tracking session: {session_id} for {operation_type}")
        return session_id
    
    def end_session(self, session_id: str = None, error_message: str = None):
        """结束操作会话"""
        if session_id is None:
            session_id = self.current_session
        
        if not session_id:
            return
        
        status = 'failed' if error_message else 'completed'
        end_time = datetime.now()
        
        # 获取开始时间计算总耗时
        row = self.db_manager.execute_query(
            "SELECT start_time, max_step_sequence FROM operation_sessions WHERE session_id = ?",
            (session_id,), fetch="one"
        )
        
        if row:
            start_time_str, max_sequence = row
            start_time = datetime.fromisoformat(start_time_str)
            total_duration = int((end_time - start_time).total_seconds() * 1000)
            
            self.db_manager.execute_query("""
                UPDATE operation_sessions 
                SET end_time = ?, total_duration = ?, status = ?, error_message = ?, updated_at = ?
                WHERE session_id = ?
            """, (end_time.isoformat(), total_duration, status, error_message, end_time.isoformat(), session_id))
        
        logger.info(f"Ended tracking session: {session_id} with status: {status}")
        
        # 清理当前线程状态
        if self.current_session == session_id:
            self.current_session = None
            self.current_step_sequence = 0
    
    def log_step(self, step: OperationStep):
        """记录操作步骤"""
        if not step.session_id:
            step.session_id = self.current_session
        
        if not step.session_id:
            logger.warning("没有活跃的会话用于步骤日志记录")
            return
        
        # 自动递增步骤序号
        if step.step_sequence == 0:
            self.current_step_sequence += 1
            step.step_sequence = self.current_step_sequence
        
        # 插入步骤记录，不设置duration，让数据库自动设置created_at时间戳
        self.db_manager.execute_query("""
            INSERT INTO operation_steps 
            (session_id, step_sequence, step_name, input_data, call_method, 
             output_data, generated_sql, error_message, success, 
             token_usage, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            step.session_id, step.step_sequence, step.step_name, step.input_data,
            step.call_method, step.output_data, step.generated_sql, step.error_message,
            step.success, json.dumps(step.token_usage.to_dict()),
            json.dumps(step.metadata)
        ))
        
        # 更新会话的最大步骤序号
        self.db_manager.execute_query("""
            UPDATE operation_sessions 
            SET max_step_sequence = MAX(max_step_sequence, ?), updated_at = ?
            WHERE session_id = ?
        """, (step.step_sequence, datetime.now().isoformat(), step.session_id))
        
        logger.debug(f"Logged step {step.step_sequence}: {step.step_name}")
    
    def add_feedback(self, feedback_type: str, feedback_sentiment: str, 
                    feedback_content: str, step_sequence: int = None,
                    feedback_user: str = None, session_id: str = None):
        """添加用户反馈"""
        if session_id is None:
            session_id = self.current_session
        
        if not session_id:
            logger.warning("没有会话用于反馈记录")
            return
        
        self.db_manager.execute_query("""
            INSERT INTO user_feedback 
            (feedback_type, session_id, step_sequence, feedback_sentiment, 
             feedback_content, feedback_user)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (feedback_type, session_id, step_sequence, feedback_sentiment,
              feedback_content, feedback_user))
        
        logger.info(f"Added {feedback_sentiment} feedback for session {session_id}")


# 全局追踪器实例
tracker = OperationTracker()


@contextmanager
def track_operation(operation_type: str, operator: str = None):
    """操作追踪上下文管理器"""
    session_id = tracker.start_session(operation_type, operator)
    try:
        yield session_id
        tracker.end_session(session_id)
    except Exception as e:
        tracker.end_session(session_id, str(e))
        raise




def extract_sql_from_text(text: str) -> str:
    """从文本中提取SQL语句"""
    if not text:
        return ""
    
    # 查找常见的SQL关键词
    sql_keywords = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'WITH', 'CREATE', 'ALTER', 'DROP']
    text_upper = text.upper()
    
    for keyword in sql_keywords:
        if keyword in text_upper:
            # 尝试提取SQL部分
            lines = text.split('\n')
            sql_lines = []
            in_sql = False
            
            for line in lines:
                line_upper = line.strip().upper()
                if any(kw in line_upper for kw in sql_keywords):
                    in_sql = True
                    sql_lines.append(line.strip())
                elif in_sql:
                    if line.strip().endswith(';') or line.strip() == '':
                        if line.strip().endswith(';'):
                            sql_lines.append(line.strip())
                        break
                    else:
                        sql_lines.append(line.strip())
            
            if sql_lines:
                return ' '.join(sql_lines)
    
    return ""


