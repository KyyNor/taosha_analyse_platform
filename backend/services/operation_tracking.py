"""
操作追踪服务 - 追踪LangGraph和大模型调用的详细信息
"""

import uuid
import time
import json
import threading
from datetime import datetime
from typing import Dict, Any, Optional, List
from contextlib import contextmanager
from functools import wraps
from dataclasses import dataclass, asdict
import sqlite3
from pathlib import Path
from loguru import logger

from config.settings import settings


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
            self.db_path = Path(settings.data_dir) / "tracking.db"
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._init_database()
            self.initialized = True
    
    def _init_database(self):
        """初始化数据库表"""
        # 读取SQL文件并执行
        sql_file = Path(__file__).parent.parent / "database" / "tracking_tables.sql"
        if sql_file.exists():
            with open(sql_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            with sqlite3.connect(self.db_path) as conn:
                conn.executescript(sql_content)
        else:
            logger.warning(f"Tracking tables SQL file not found: {sql_file}")
    
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
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO operation_sessions 
                (session_id, operation_type, operator, start_time, status)
                VALUES (?, ?, ?, ?, 'running')
            """, (session_id, operation_type, operator, datetime.now()))
        
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
        
        with sqlite3.connect(self.db_path) as conn:
            # 获取开始时间计算总耗时
            cursor = conn.execute(
                "SELECT start_time, max_step_sequence FROM operation_sessions WHERE session_id = ?",
                (session_id,)
            )
            row = cursor.fetchone()
            
            if row:
                start_time_str, max_sequence = row
                start_time = datetime.fromisoformat(start_time_str)
                total_duration = int((end_time - start_time).total_seconds() * 1000)
                
                conn.execute("""
                    UPDATE operation_sessions 
                    SET end_time = ?, total_duration = ?, status = ?, error_message = ?, updated_at = ?
                    WHERE session_id = ?
                """, (end_time, total_duration, status, error_message, end_time, session_id))
        
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
            logger.warning("No active session for step logging")
            return
        
        # 自动递增步骤序号
        if step.step_sequence == 0:
            self.current_step_sequence += 1
            step.step_sequence = self.current_step_sequence
        
        with sqlite3.connect(self.db_path) as conn:
            # 插入步骤记录
            conn.execute("""
                INSERT INTO operation_steps 
                (session_id, step_sequence, step_name, input_data, call_method, 
                 output_data, generated_sql, error_message, success, duration, 
                 token_usage, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                step.session_id, step.step_sequence, step.step_name, step.input_data,
                step.call_method, step.output_data, step.generated_sql, step.error_message,
                step.success, step.duration, json.dumps(step.token_usage.to_dict()),
                json.dumps(step.metadata)
            ))
            
            # 更新会话的最大步骤序号
            conn.execute("""
                UPDATE operation_sessions 
                SET max_step_sequence = MAX(max_step_sequence, ?), updated_at = ?
                WHERE session_id = ?
            """, (step.step_sequence, datetime.now(), step.session_id))
        
        logger.debug(f"Logged step {step.step_sequence}: {step.step_name}")
    
    def add_feedback(self, feedback_type: str, feedback_sentiment: str, 
                    feedback_content: str, step_sequence: int = None,
                    feedback_user: str = None, session_id: str = None):
        """添加用户反馈"""
        if session_id is None:
            session_id = self.current_session
        
        if not session_id:
            logger.warning("No session for feedback")
            return
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
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


def track_step(step_name: str, call_method: str = "", auto_extract_sql: bool = True):
    """步骤追踪装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not tracker.current_session:
                # 如果没有活跃会话，直接执行原函数
                return func(*args, **kwargs)
            
            step = OperationStep(
                session_id=tracker.current_session,
                step_sequence=0,  # 自动分配
                step_name=step_name,
                call_method=call_method or f"{func.__module__}.{func.__name__}"
            )
            
            # 记录输入参数
            input_data = {
                'args': [str(arg)[:200] for arg in args],  # 限制长度
                'kwargs': {k: str(v)[:200] for k, v in kwargs.items()}
            }
            step.input_data = json.dumps(input_data, ensure_ascii=False)
            
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                step.duration = int((time.time() - start_time) * 1000)
                step.success = True
                
                # 记录输出结果
                if result is not None:
                    result_str = str(result)
                    step.output_data = result_str[:1000]  # 限制长度
                    
                    # 自动提取SQL
                    if auto_extract_sql and isinstance(result, str):
                        step.generated_sql = extract_sql_from_text(result)
                
                tracker.log_step(step)
                return result
                
            except Exception as e:
                step.duration = int((time.time() - start_time) * 1000)
                step.success = False
                step.error_message = str(e)
                tracker.log_step(step)
                raise
        
        return wrapper
    return decorator


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


def get_session_logs(session_id: str) -> Dict[str, Any]:
    """获取会话的完整日志"""
    with sqlite3.connect(tracker.db_path) as conn:
        # 获取会话信息
        cursor = conn.execute("""
            SELECT * FROM operation_sessions WHERE session_id = ?
        """, (session_id,))
        session_row = cursor.fetchone()
        
        if not session_row:
            return {}
        
        # 获取步骤信息
        cursor = conn.execute("""
            SELECT * FROM operation_steps WHERE session_id = ? ORDER BY step_sequence
        """, (session_id,))
        step_rows = cursor.fetchall()
        
        # 获取反馈信息
        cursor = conn.execute("""
            SELECT * FROM user_feedback WHERE session_id = ? ORDER BY feedback_time
        """, (session_id,))
        feedback_rows = cursor.fetchall()
        
        return {
            'session': dict(zip([col[0] for col in cursor.description], session_row)) if session_row else {},
            'steps': [dict(zip([col[0] for col in cursor.description], row)) for row in step_rows],
            'feedback': [dict(zip([col[0] for col in cursor.description], row)) for row in feedback_rows]
        }


def get_recent_sessions(limit: int = 50) -> List[Dict[str, Any]]:
    """获取最近的会话列表"""
    with sqlite3.connect(tracker.db_path) as conn:
        cursor = conn.execute("""
            SELECT session_id, operation_type, operator, start_time, end_time, 
                   total_duration, max_step_sequence, status, error_message
            FROM operation_sessions 
            ORDER BY start_time DESC 
            LIMIT ?
        """, (limit,))
        
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]