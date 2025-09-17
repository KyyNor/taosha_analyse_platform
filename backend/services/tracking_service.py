"""
追踪数据查询服务
"""

import sqlite3
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass

from services.operation_tracking import tracker


@dataclass
class SessionSummary:
    """会话摘要"""
    session_id: str
    operation_type: str
    operator: str
    start_time: datetime
    end_time: Optional[datetime]
    total_duration: Optional[int]
    step_count: int
    success_rate: float
    status: str
    error_message: Optional[str]


@dataclass
class StepSummary:
    """步骤摘要"""
    step_sequence: int
    step_name: str
    call_method: str
    success: bool
    duration: int
    error_message: Optional[str]
    has_sql: bool


class TrackingService:
    """追踪数据查询服务"""
    
    def __init__(self):
        self.db_path = tracker.db_path
    
    def get_session_summary(self, session_id: str) -> Optional[SessionSummary]:
        """获取会话摘要"""
        with sqlite3.connect(self.db_path) as conn:
            # 获取会话基本信息
            cursor = conn.execute("""
                SELECT session_id, operation_type, operator, start_time, end_time,
                       total_duration, max_step_sequence, status, error_message
                FROM operation_sessions 
                WHERE session_id = ?
            """, (session_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            # 获取步骤统计信息
            cursor = conn.execute("""
                SELECT COUNT(*) as total_steps, 
                       SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_steps
                FROM operation_steps 
                WHERE session_id = ?
            """, (session_id,))
            
            step_stats = cursor.fetchone()
            total_steps, success_steps = step_stats if step_stats else (0, 0)
            success_rate = (success_steps / total_steps * 100) if total_steps > 0 else 0
            
            session_data = row
            return SessionSummary(
                session_id=session_data[0],
                operation_type=session_data[1],
                operator=session_data[2],
                start_time=datetime.fromisoformat(session_data[3]) if session_data[3] else None,
                end_time=datetime.fromisoformat(session_data[4]) if session_data[4] else None,
                total_duration=session_data[5],
                step_count=total_steps,
                success_rate=success_rate,
                status=session_data[7],
                error_message=session_data[8]
            )
    
    def get_session_steps(self, session_id: str) -> List[StepSummary]:
        """获取会话的所有步骤"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT step_sequence, step_name, call_method, success, duration,
                       error_message, generated_sql
                FROM operation_steps 
                WHERE session_id = ?
                ORDER BY step_sequence
            """, (session_id,))
            
            steps = []
            for row in cursor.fetchall():
                steps.append(StepSummary(
                    step_sequence=row[0],
                    step_name=row[1],
                    call_method=row[2],
                    success=bool(row[3]),
                    duration=row[4],
                    error_message=row[5],
                    has_sql=bool(row[6])
                ))
            
            return steps
    
    def get_recent_sessions(self, limit: int = 50, operator: str = None) -> List[SessionSummary]:
        """获取最近的会话列表"""
        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT s.session_id, s.operation_type, s.operator, s.start_time, s.end_time,
                       s.total_duration, s.max_step_sequence, s.status, s.error_message,
                       COUNT(st.id) as total_steps,
                       SUM(CASE WHEN st.success = 1 THEN 1 ELSE 0 END) as success_steps
                FROM operation_sessions s
                LEFT JOIN operation_steps st ON s.session_id = st.session_id
            """
            
            params = []
            if operator:
                query += " WHERE s.operator = ?"
                params.append(operator)
            
            query += """
                GROUP BY s.session_id
                ORDER BY s.start_time DESC 
                LIMIT ?
            """
            params.append(limit)
            
            cursor = conn.execute(query, params)
            
            sessions = []
            for row in cursor.fetchall():
                total_steps = row[9] or 0
                success_steps = row[10] or 0
                success_rate = (success_steps / total_steps * 100) if total_steps > 0 else 0
                
                sessions.append(SessionSummary(
                    session_id=row[0],
                    operation_type=row[1],
                    operator=row[2],
                    start_time=datetime.fromisoformat(row[3]) if row[3] else None,
                    end_time=datetime.fromisoformat(row[4]) if row[4] else None,
                    total_duration=row[5],
                    step_count=total_steps,
                    success_rate=success_rate,
                    status=row[7],
                    error_message=row[8]
                ))
            
            return sessions
    
    def get_operation_stats(self, days: int = 7) -> Dict[str, Any]:
        """获取操作统计信息"""
        since_date = datetime.now() - timedelta(days=days)
        
        with sqlite3.connect(self.db_path) as conn:
            # 总体统计
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_sessions,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_sessions,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_sessions,
                    AVG(total_duration) as avg_duration,
                    AVG(max_step_sequence) as avg_steps
                FROM operation_sessions 
                WHERE start_time >= ?
            """, (since_date.isoformat(),))
            
            overall_stats = cursor.fetchone()
            
            # 按操作类型统计
            cursor = conn.execute("""
                SELECT operation_type, 
                       COUNT(*) as count,
                       AVG(total_duration) as avg_duration,
                       SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as success_count
                FROM operation_sessions 
                WHERE start_time >= ?
                GROUP BY operation_type
                ORDER BY count DESC
            """, (since_date.isoformat(),))
            
            operation_stats = []
            for row in cursor.fetchall():
                operation_stats.append({
                    'operation_type': row[0],
                    'count': row[1],
                    'avg_duration': row[2],
                    'success_rate': (row[3] / row[1] * 100) if row[1] > 0 else 0
                })
            
            # 按时间统计（每日）
            cursor = conn.execute("""
                SELECT DATE(start_time) as date,
                       COUNT(*) as sessions,
                       SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as success_sessions
                FROM operation_sessions 
                WHERE start_time >= ?
                GROUP BY DATE(start_time)
                ORDER BY date DESC
            """, (since_date.isoformat(),))
            
            daily_stats = []
            for row in cursor.fetchall():
                daily_stats.append({
                    'date': row[0],
                    'sessions': row[1],
                    'success_rate': (row[2] / row[1] * 100) if row[1] > 0 else 0
                })
            
            return {
                'overall': {
                    'total_sessions': overall_stats[0] or 0,
                    'completed_sessions': overall_stats[1] or 0,
                    'failed_sessions': overall_stats[2] or 0,
                    'success_rate': ((overall_stats[1] or 0) / (overall_stats[0] or 1) * 100),
                    'avg_duration': overall_stats[3] or 0,
                    'avg_steps': overall_stats[4] or 0
                },
                'by_operation_type': operation_stats,
                'daily_stats': daily_stats
            }
    
    def get_step_details(self, session_id: str, step_sequence: int) -> Optional[Dict[str, Any]]:
        """获取步骤详细信息"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM operation_steps 
                WHERE session_id = ? AND step_sequence = ?
            """, (session_id, step_sequence))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            columns = [col[0] for col in cursor.description]
            step_data = dict(zip(columns, row))
            
            # 解析JSON字段
            import json
            try:
                step_data['token_usage'] = json.loads(step_data['token_usage']) if step_data['token_usage'] else {}
                step_data['metadata'] = json.loads(step_data['metadata']) if step_data['metadata'] else {}
            except json.JSONDecodeError:
                step_data['token_usage'] = {}
                step_data['metadata'] = {}
            
            return step_data
    
    def search_sessions(self, query: str, limit: int = 20) -> List[SessionSummary]:
        """搜索会话（根据操作类型、操作人等）"""
        with sqlite3.connect(self.db_path) as conn:
            search_query = f"%{query}%"
            cursor = conn.execute("""
                SELECT s.session_id, s.operation_type, s.operator, s.start_time, s.end_time,
                       s.total_duration, s.max_step_sequence, s.status, s.error_message,
                       COUNT(st.id) as total_steps,
                       SUM(CASE WHEN st.success = 1 THEN 1 ELSE 0 END) as success_steps
                FROM operation_sessions s
                LEFT JOIN operation_steps st ON s.session_id = st.session_id
                WHERE s.operation_type LIKE ? OR s.operator LIKE ? OR s.session_id LIKE ?
                GROUP BY s.session_id
                ORDER BY s.start_time DESC 
                LIMIT ?
            """, (search_query, search_query, search_query, limit))
            
            sessions = []
            for row in cursor.fetchall():
                total_steps = row[9] or 0
                success_steps = row[10] or 0
                success_rate = (success_steps / total_steps * 100) if total_steps > 0 else 0
                
                sessions.append(SessionSummary(
                    session_id=row[0],
                    operation_type=row[1],
                    operator=row[2],
                    start_time=datetime.fromisoformat(row[3]) if row[3] else None,
                    end_time=datetime.fromisoformat(row[4]) if row[4] else None,
                    total_duration=row[5],
                    step_count=total_steps,
                    success_rate=success_rate,
                    status=row[7],
                    error_message=row[8]
                ))
            
            return sessions


# 全局服务实例
_tracking_service: Optional[TrackingService] = None

def get_tracking_service() -> TrackingService:
    """获取追踪服务实例"""
    global _tracking_service
    if _tracking_service is None:
        _tracking_service = TrackingService()
    return _tracking_service