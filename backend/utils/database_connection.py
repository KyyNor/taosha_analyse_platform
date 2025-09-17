"""
统一数据库连接管理
"""

import sqlite3
import pymysql
from typing import Dict, Any, Optional, Union
from contextlib import contextmanager
from loguru import logger
from pathlib import Path

from config.settings import settings


class DatabaseConnectionManager:
    """数据库连接管理器"""
    
    def __init__(self):
        self._connections: Dict[str, Any] = {}
    
    def get_metadata_db_config(self) -> Dict[str, Any]:
        """获取元数据数据库配置"""
        return {
            "type": getattr(settings, "metadata_db_type", "sqlite"),
            "config": self._get_db_config_by_type(getattr(settings, "metadata_db_type", "sqlite"))
        }
    
    def _get_db_config_by_type(self, db_type: str) -> Dict[str, Any]:
        """根据数据库类型获取配置"""
        if db_type == "sqlite":
            return {
                "database": str(settings.database_dir / "metadata.db")
            }
        elif db_type == "mysql":
            return {
                "host": getattr(settings, "metadata_mysql_host", "localhost"),
                "port": getattr(settings, "metadata_mysql_port", 3306),
                "database": getattr(settings, "metadata_mysql_database", "taosha_metadata"),
                "user": getattr(settings, "metadata_mysql_user", "root"),
                "password": getattr(settings, "metadata_mysql_password", ""),
                "charset": getattr(settings, "metadata_mysql_charset", "utf8mb4")
            }
        else:
            raise ValueError(f"不支持的数据库类型: {db_type}")
    
    def create_connection(self, db_type: str, config: Dict[str, Any]):
        """创建数据库连接"""
        if db_type == "sqlite":
            # 确保数据库目录存在
            db_path = Path(config["database"])
            db_path.parent.mkdir(parents=True, exist_ok=True)
            return sqlite3.connect(config["database"])
        elif db_type == "mysql":
            # pymysql推荐配置
            mysql_config = {
                'autocommit': False,
                'cursorclass': pymysql.cursors.Cursor,
                **config  # 包含从settings来的charset配置
            }
            return pymysql.connect(**mysql_config)
        else:
            raise ValueError(f"不支持的数据库类型: {db_type}")
    
    @contextmanager
    def get_metadata_connection(self):
        """获取元数据数据库连接（上下文管理器）"""
        db_config = self.get_metadata_db_config()
        db_type = db_config["type"]
        config = db_config["config"]
        
        conn = None
        try:
            conn = self.create_connection(db_type, config)
            logger.debug(f"创建{db_type}数据库连接")
            yield conn, db_type
            # 如果没有异常，自动提交事务
            conn.commit()
            logger.debug(f"事务已提交: {db_type}")
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            if conn:
                conn.rollback()
                logger.debug(f"事务已回滚: {db_type}")
            raise
        finally:
            if conn:
                conn.close()
                logger.debug(f"关闭{db_type}数据库连接")
    
    def init_metadata_tables(self, force_recreate: bool = False):
        """初始化元数据表结构
        
        Args:
            force_recreate: 如果为True，将删除所有表并重新创建
        """
        db_config = self.get_metadata_db_config()
        db_type = db_config["type"]
        
        # 如果需要强制重建且是SQLite，删除数据库文件
        if force_recreate and db_type == "sqlite":
            db_path = Path(db_config["config"]["database"])
            if db_path.exists():
                db_path.unlink()
                logger.info(f"SQLite数据库文件已删除: {db_path}")
        
        with self.get_metadata_connection() as (conn, db_type):
            cursor = conn.cursor()
            
            try:
                # 如果需要强制重建且是MySQL，删除所有表
                if force_recreate and db_type == "mysql":
                    self._drop_mysql_tables(cursor)
                
                if db_type == "sqlite":
                    self._create_sqlite_metadata_tables(cursor)
                elif db_type == "mysql":
                    self._create_mysql_metadata_tables(cursor)
                
                conn.commit()
                action = "重建完成" if force_recreate else "初始化完成"
                logger.info(f"元数据表{action}: {db_type}")
                
            except Exception as e:
                logger.error(f"元数据表初始化失败: {e}")
                conn.rollback()
                raise
    
    def _drop_mysql_tables(self, cursor):
        """删除MySQL中的所有元数据表"""
        tables_to_drop = [
            'user_feedback',
            'operation_steps',
            'operation_sessions',
            'glossary_aliases',
            'glossary_terms', 
            'metadata_columns',
            'metadata_tables',
            'relation_field_config'
        ]
        
        # 先禁用外键约束检查
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        
        for table in tables_to_drop:
            try:
                cursor.execute(f"DROP TABLE IF EXISTS {table}")
                logger.debug(f"已删除表: {table}")
            except Exception as e:
                logger.warning(f"删除表{table}失败: {e}")
        
        # 重新启用外键约束检查
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
    
    def _create_sqlite_metadata_tables(self, cursor):
        """创建SQLite元数据表"""
        # 元数据表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metadata_tables (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                comment TEXT,
                is_available INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metadata_columns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_name TEXT NOT NULL,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                comment TEXT,
                is_available INTEGER DEFAULT 0,
                business_type TEXT DEFAULT '',
                relation_id TEXT DEFAULT '',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (table_name) REFERENCES metadata_tables(name) ON DELETE CASCADE,
                UNIQUE(table_name, name)
            )
        """)
        
        # 术语表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS glossary_terms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                term TEXT UNIQUE NOT NULL,
                definition TEXT,
                sql_expression TEXT,
                category TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS glossary_aliases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                term_id INTEGER NOT NULL,
                alias TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (term_id) REFERENCES glossary_terms(id) ON DELETE CASCADE,
                UNIQUE(alias)
            )
        """)
        
        # 关联字段配置表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS relation_field_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                relation_id TEXT UNIQUE NOT NULL,
                relation_family TEXT NOT NULL,
                relation_subfamily TEXT NOT NULL,
                relation_desc TEXT DEFAULT '',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 操作追踪表
        self._create_sqlite_tracking_tables(cursor)
    
    def _create_mysql_metadata_tables(self, cursor):
        """创建MySQL元数据表"""
        # 元数据表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metadata_tables (
                id INT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(255) UNIQUE NOT NULL,
                comment TEXT,
                is_available INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metadata_columns (
                id INT PRIMARY KEY AUTO_INCREMENT,
                table_name VARCHAR(255) NOT NULL,
                name VARCHAR(255) NOT NULL,
                type VARCHAR(100) NOT NULL,
                comment TEXT,
                is_available INT DEFAULT 0,
                business_type VARCHAR(100) DEFAULT '',
                relation_id VARCHAR(255) DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (table_name) REFERENCES metadata_tables(name) ON DELETE CASCADE,
                UNIQUE KEY unique_table_column (table_name, name)
            )
        """)
        
        # 术语表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS glossary_terms (
                id INT PRIMARY KEY AUTO_INCREMENT,
                term VARCHAR(255) UNIQUE NOT NULL,
                definition TEXT,
                sql_expression TEXT,
                category VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS glossary_aliases (
                id INT PRIMARY KEY AUTO_INCREMENT,
                term_id INT NOT NULL,
                alias VARCHAR(255) NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (term_id) REFERENCES glossary_terms(id) ON DELETE CASCADE
            )
        """)
        
        # 关联字段配置表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS relation_field_config (
                id INT PRIMARY KEY AUTO_INCREMENT,
                relation_id VARCHAR(255) UNIQUE NOT NULL,
                relation_family VARCHAR(255) NOT NULL,
                relation_subfamily VARCHAR(255) NOT NULL,
                relation_desc TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)
        
        # 操作追踪表
        self._create_mysql_tracking_tables(cursor)
    
    def _create_sqlite_tracking_tables(self, cursor):
        """创建SQLite追踪表"""
        # 操作会话记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS operation_sessions (
                session_id TEXT PRIMARY KEY,
                operation_type TEXT NOT NULL,
                operator TEXT,
                start_time DATETIME NOT NULL,
                end_time DATETIME,
                total_duration INTEGER,
                max_step_sequence INTEGER DEFAULT 0,
                status TEXT DEFAULT 'running',
                error_message TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 操作步骤详情表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS operation_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                step_sequence INTEGER NOT NULL,
                step_name TEXT NOT NULL,
                input_data TEXT,
                call_method TEXT,
                output_data TEXT,
                generated_sql TEXT,
                error_message TEXT,
                success INTEGER DEFAULT 1,
                duration INTEGER,
                token_usage TEXT,
                metadata TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES operation_sessions(session_id)
            )
        """)
        
        # 用户反馈表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feedback_type TEXT NOT NULL,
                session_id TEXT NOT NULL,
                step_sequence INTEGER,
                feedback_sentiment TEXT NOT NULL,
                feedback_content TEXT NOT NULL,
                feedback_user TEXT,
                feedback_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES operation_sessions(session_id)
            )
        """)
        
        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_operation_sessions_operator ON operation_sessions(operator)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_operation_sessions_operation_type ON operation_sessions(operation_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_operation_sessions_start_time ON operation_sessions(start_time)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_operation_steps_session_id ON operation_steps(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_operation_steps_step_sequence ON operation_steps(session_id, step_sequence)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_feedback_session_id ON user_feedback(session_id)")
    
    def _create_mysql_tracking_tables(self, cursor):
        """创建MySQL追踪表"""
        # 操作会话记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS operation_sessions (
                session_id VARCHAR(36) PRIMARY KEY,
                operation_type VARCHAR(100) NOT NULL,
                operator VARCHAR(100),
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP NULL,
                total_duration INT,
                max_step_sequence INT DEFAULT 0,
                status VARCHAR(20) DEFAULT 'running',
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)
        
        # 操作步骤详情表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS operation_steps (
                id INT PRIMARY KEY AUTO_INCREMENT,
                session_id VARCHAR(36) NOT NULL,
                step_sequence INT NOT NULL,
                step_name VARCHAR(200) NOT NULL,
                input_data TEXT,
                call_method VARCHAR(100),
                output_data TEXT,
                generated_sql TEXT,
                error_message TEXT,
                success BOOLEAN DEFAULT TRUE,
                duration INT,
                token_usage JSON,
                metadata JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES operation_sessions(session_id)
            )
        """)
        
        # 用户反馈表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_feedback (
                id INT PRIMARY KEY AUTO_INCREMENT,
                feedback_type VARCHAR(50) NOT NULL,
                session_id VARCHAR(36) NOT NULL,
                step_sequence INT,
                feedback_sentiment VARCHAR(20) NOT NULL,
                feedback_content TEXT NOT NULL,
                feedback_user VARCHAR(100),
                feedback_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES operation_sessions(session_id)
            )
        """)
        
        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_operation_sessions_operator ON operation_sessions(operator)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_operation_sessions_operation_type ON operation_sessions(operation_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_operation_sessions_start_time ON operation_sessions(start_time)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_operation_steps_session_id ON operation_steps(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_feedback_session_id ON user_feedback(session_id)")
    
    def get_sql_placeholder(self, db_type: str) -> str:
        """获取SQL占位符"""
        if db_type == "sqlite":
            return "?"
        elif db_type == "mysql":
            return "%s"
        else:
            raise ValueError(f"不支持的数据库类型: {db_type}")
    
    def execute_query(self, query: str, params: tuple = None, fetch: str = "none") -> Optional[Any]:
        """执行查询"""
        with self.get_metadata_connection() as (conn, db_type):
            cursor = conn.cursor()
            
            # 转换占位符
            if db_type == "mysql" and "?" in query:
                query = query.replace("?", "%s")
            
            try:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                if fetch == "one":
                    result = cursor.fetchone()
                elif fetch == "all":
                    result = cursor.fetchall()
                elif fetch == "lastrowid":
                    result = cursor.lastrowid
                else:
                    result = None
                
                conn.commit()
                return result
                
            except Exception as e:
                logger.error(f"SQL执行失败: {e}, SQL: {query}, 参数: {params}")
                conn.rollback()
                raise


# 全局数据库连接管理器实例
_db_manager: Optional[DatabaseConnectionManager] = None


def get_database_manager() -> DatabaseConnectionManager:
    """获取数据库连接管理器实例"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseConnectionManager()
        # 初始化元数据表（强制重建以支持新字段）
        try:
            # init_metadata_tables(force_recreate=True) 可以强制重建
            _db_manager.init_metadata_tables()
        except Exception as e:
            logger.warning(f"元数据表初始化失败，但继续运行: {e}")
    return _db_manager