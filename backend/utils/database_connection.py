"""
统一数据库连接管理
"""

import sqlite3
import pymysql
from typing import Dict, Any, Optional, Union
from contextlib import contextmanager
from loguru import logger
from pathlib import Path

from config import settings


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
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
                logger.debug(f"关闭{db_type}数据库连接")
    
    def init_metadata_tables(self):
        """初始化元数据表结构"""
        with self.get_metadata_connection() as (conn, db_type):
            cursor = conn.cursor()
            
            try:
                if db_type == "sqlite":
                    self._create_sqlite_metadata_tables(cursor)
                elif db_type == "mysql":
                    self._create_mysql_metadata_tables(cursor)
                
                conn.commit()
                logger.info(f"元数据表初始化完成: {db_type}")
                
            except Exception as e:
                logger.error(f"元数据表初始化失败: {e}")
                conn.rollback()
                raise
    
    def _create_sqlite_metadata_tables(self, cursor):
        """创建SQLite元数据表"""
        # 元数据表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metadata_tables (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                comment TEXT,
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
                is_primary_key BOOLEAN DEFAULT FALSE,
                is_nullable BOOLEAN DEFAULT TRUE,
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
    
    def _create_mysql_metadata_tables(self, cursor):
        """创建MySQL元数据表"""
        # 元数据表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metadata_tables (
                id INT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(255) UNIQUE NOT NULL,
                comment TEXT,
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
                is_primary_key BOOLEAN DEFAULT FALSE,
                is_nullable BOOLEAN DEFAULT TRUE,
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
        # 初始化元数据表
        try:
            _db_manager.init_metadata_tables()
        except Exception as e:
            logger.warning(f"元数据表初始化失败，但继续运行: {e}")
    return _db_manager