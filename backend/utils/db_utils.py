"""
统一数据库连接管理
"""

import sqlite3
import pymysql
from typing import Dict, Any, Optional, Union
from contextlib import contextmanager
from utils.logger import logger
from pathlib import Path

from utils.config import settings


class DatabaseConnectionManager:
    """数据库连接管理器"""
    
    def __init__(self):
        self._connections: Dict[str, Any] = {}
    
    def get_taosha_db_config(self) -> Dict[str, Any]:
        """获取元数据数据库配置"""
        return {
            "type": getattr(settings, "taosha_db_type", "sqlite"),
            "config": self._get_db_config_by_type(getattr(settings, "taosha_db_type", "sqlite"))
        }
    
    def _get_db_config_by_type(self, db_type: str) -> Dict[str, Any]:
        """根据数据库类型获取配置"""
        if db_type == "sqlite":
            return {
                "database": str(settings.database_dir / "metadata.db")
            }
        elif db_type == "mysql":
            return {
                "host": getattr(settings, "taosha_db_mysql_host", "localhost"),
                "port": getattr(settings, "taosha_db_mysql_port", 3306),
                "database": getattr(settings, "taosha_db_mysql_database", "taosha"),
                "user": getattr(settings, "taosha_db_mysql_user", "root"),
                "password": getattr(settings, "taosha_db_mysql_password", ""),
                "charset": getattr(settings, "taosha_db_mysql_charset", "utf8mb4")
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
    def get_taosha_db_connection(self):
        """获取元数据数据库连接（上下文管理器）"""
        db_config = self.get_taosha_db_config()
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
    
    def init_taosha_db_tables(self, force_recreate: bool = False):
        """初始化元数据表结构

        Args:
            force_recreate: 如果为True，将删除所有表并重新创建
        """
        from pathlib import Path

        db_config = self.get_taosha_db_config()
        db_type = db_config["type"]

        # 如果需要强制重建且是SQLite，删除数据库文件
        if force_recreate and db_type == "sqlite":
            db_path = Path(db_config["config"]["database"])
            if db_path.exists():
                db_path.unlink()
                logger.info(f"SQLite数据库文件已删除: {db_path}")

        with self.get_taosha_db_connection() as (conn, db_type):
            cursor = conn.cursor()

            try:
                # 如果需要强制重建且是MySQL，执行删除表脚本
                if force_recreate and db_type == "mysql":
                    self._execute_sql_file(cursor, "../sql/drop_tables_mysql.sql")

                # 执行建表脚本
                if db_type == "sqlite":
                    self._execute_sql_file(cursor, "../sql/create_tables.sql")
                elif db_type == "mysql":
                    self._execute_sql_file(cursor, "../sql/create_tables_mysql.sql")

                conn.commit()
                action = "重建完成" if force_recreate else "初始化完成"
                logger.info(f"元数据表{action}: {db_type}")

            except Exception as e:
                logger.error(f"元数据表初始化失败: {e}")
                conn.rollback()
                raise

    def _execute_sql_file(self, cursor, file_path: str):
        """执行SQL文件"""
        from pathlib import Path

        sql_file = Path(__file__).parent / file_path
        if not sql_file.exists():
            raise FileNotFoundError(f"SQL文件不存在: {sql_file}")

        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()

        # 分割SQL语句（以分号分隔）
        statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]

        for statement in statements:
            if statement:
                try:
                    cursor.execute(statement)
                    logger.debug(f"执行SQL: {statement[:100]}...")
                except Exception as e:
                    logger.warning(f"SQL执行失败: {e}, SQL: {statement[:100]}...")
                    # 不是所有错误都需要抛出异常（如表已存在等）

    def get_sql_placeholder(self, db_type: str) -> str:
        """获取SQL占位符"""
        if db_type == "sqlite":
            return "?"
        elif db_type == "mysql":
            return "%s"
        else:
            raise ValueError(f"不支持的数据库类型: {db_type}")
    
    def execute_query(self, query: str, params: tuple = None, fetch: str = "all", return_dict: bool = True) -> Optional[Any]:
        """执行查询

        Args:
            query: SQL查询语句
            params: 查询参数
            fetch: 获取结果的方式 ("none", "one", "all", "lastrowid")
            return_dict: 是否返回字典格式 (True) 或元组格式 (False)，默认True

        Returns:
            根据fetch和return_dict参数返回相应格式的结果
        """
        with self.get_taosha_db_connection() as (conn, db_type):
            # 根据return_dict选择cursor类型
            if return_dict:
                if db_type == "sqlite":
                    cursor = conn.cursor()
                    cursor.row_factory = sqlite3.Row
                elif db_type == "mysql":
                    cursor = conn.cursor(pymysql.cursors.DictCursor)
                else:
                    cursor = conn.cursor()
            else:
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
                    # 将sqlite.Row转换为字典
                    if return_dict and db_type == "sqlite" and result is not None:
                        result = dict(result)
                elif fetch == "all":
                    result = cursor.fetchall()
                    # 将sqlite.Row列表转换为字典列表
                    if return_dict and db_type == "sqlite":
                        result = [dict(row) for row in result]
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
        # try:
            # init_metadata_tables(force_recreate=True) 可以强制重建
            # _db_manager.init_metadata_tables()
        # except Exception as e:
            # logger.warning(f"元数据表初始化失败，但继续运行: {e}")
    return _db_manager