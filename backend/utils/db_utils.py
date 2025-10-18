"""
统一数据库连接管理 - SQLAlchemy版本
"""

from typing import Dict, Any, Optional, List
from contextlib import contextmanager
from sqlalchemy.orm import Session
from sqlalchemy import text
from utils.logger import logger
from utils.config import settings
from models.base import engine, SessionLocal, create_tables, drop_tables, reset_database


class DatabaseConnectionManager:
    """数据库连接管理器 - SQLAlchemy版本"""

    def __init__(self):
        self._initialized = False

    def get_taosha_db_config(self) -> Dict[str, Any]:
        """获取元数据数据库配置"""
        return {
            "type": getattr(settings, "taosha_db_type", "sqlite"),
            "url": self._get_database_url()
        }

    def _get_database_url(self) -> str:
        """获取数据库连接URL"""
        db_type = getattr(settings, 'taosha_db_type', 'sqlite')

        if db_type == 'sqlite':
            db_path = str(settings.database_dir / 'metadata.db')
            return f"sqlite:///{db_path}"
        elif db_type == 'mysql':
            host = getattr(settings, 'taosha_db_mysql_host', 'localhost')
            port = getattr(settings, 'taosha_db_mysql_port', 3306)
            database = getattr(settings, 'taosha_db_mysql_database', 'taosha')
            user = getattr(settings, 'taosha_db_mysql_user', 'root')
            password = getattr(settings, 'taosha_db_mysql_password', '')
            charset = getattr(settings, 'taosha_db_mysql_charset', 'utf8mb4')
            return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset={charset}"
        else:
            raise ValueError(f"不支持的数据库类型: {db_type}")

    @contextmanager
    def get_taosha_db_connection(self):
        """获取数据库连接（上下文管理器）"""
        db = SessionLocal()
        try:
            yield db, self.get_taosha_db_config()["type"]
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"数据库操作失败: {e}")
            raise
        finally:
            db.close()

    def init_taosha_db_tables(self, force_recreate: bool = False):
        """初始化元数据表结构

        Args:
            force_recreate: 如果为True，将删除所有表并重新创建
        """
        try:
            if force_recreate:
                logger.info("强制重建数据库表...")
                reset_database()
            else:
                create_tables()

            action = "重建完成" if force_recreate else "初始化完成"
            logger.info(f"元数据表{action}")
        except Exception as e:
            logger.error(f"元数据表初始化失败: {e}")
            raise

    def execute_query(self, query: str, params: tuple = None, fetch: str = "all", return_dict: bool = True) -> Optional[Any]:
        """执行查询（兼容原接口）

        Args:
            query: SQL查询语句
            params: 查询参数
            fetch: 获取结果的方式 ("none", "one", "all", "lastrowid")
            return_dict: 是否返回字典格式（为了兼容性保留）

        Returns:
            根据fetch参数返回相应格式的结果
        """
        try:
            with self.get_taosha_db_connection() as (db, db_type):
                # 转换MySQL占位符
                if db_type == "mysql" and "?" in query:
                    query = query.replace("?", "%s")

                result = db.execute(text(query), params or ())

                if fetch == "one":
                    row = result.fetchone()
                    if row and return_dict:
                        return dict(row._mapping)
                    return row
                elif fetch == "all":
                    rows = result.fetchall()
                    if return_dict:
                        return [dict(row._mapping) for row in rows]
                    return rows
                elif fetch == "lastrowid":
                    # 对于插入操作，返回最后插入的行ID
                    if hasattr(result, 'lastrowid'):
                        return result.lastrowid
                    # 如果没有lastrowid属性，尝试通过查询获取
                    if "INSERT" in query.upper():
                        # 这里需要根据具体表结构来获取ID
                        # 为了兼容性，返回None
                        logger.warning("无法获取lastrowid，返回None")
                    return None
                else:
                    return None

        except Exception as e:
            logger.error(f"SQL执行失败: {e}, SQL: {query}, 参数: {params}")
            raise

    def get_sql_placeholder(self, db_type: str) -> str:
        """获取SQL占位符"""
        if db_type == "sqlite":
            return "?"
        elif db_type == "mysql":
            return "%s"
        else:
            raise ValueError(f"不支持的数据库类型: {db_type}")

    def execute_raw_sql(self, sql: str, params: dict = None) -> Any:
        """执行原生SQL语句

        Args:
            sql: SQL语句
            params: 参数字典

        Returns:
            执行结果
        """
        try:
            with self.get_taosha_db_connection() as (db, db_type):
                result = db.execute(text(sql), params or {})
                return result
        except Exception as e:
            logger.error(f"执行原生SQL失败: {e}, SQL: {sql}")
            raise

    def get_session(self) -> Session:
        """获取数据库会话"""
        return SessionLocal()

    def test_connection(self) -> bool:
        """测试数据库连接"""
        try:
            with self.get_taosha_db_connection() as (db, db_type):
                db.execute(text("SELECT 1"))
            logger.info("数据库连接测试成功")
            return True
        except Exception as e:
            logger.error(f"数据库连接测试失败: {e}")
            return False

    def get_database_info(self) -> Dict[str, Any]:
        """获取数据库信息"""
        try:
            with self.get_taosha_db_connection() as (db, db_type):
                # 获取表列表
                if db_type == "sqlite":
                    tables_result = db.execute(text(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    )).fetchall()
                else:  # MySQL
                    tables_result = db.execute(text(
                        "SHOW TABLES"
                    )).fetchall()

                tables = [row[0] for row in tables_result] if tables_result else []

                return {
                    "database_type": db_type,
                    "database_url": self._get_database_url(),
                    "tables": tables,
                    "table_count": len(tables)
                }
        except Exception as e:
            logger.error(f"获取数据库信息失败: {e}")
            return {
                "database_type": getattr(settings, 'taosha_db_type', 'sqlite'),
                "database_url": self._get_database_url(),
                "tables": [],
                "table_count": 0,
                "error": str(e)
            }


# 全局数据库连接管理器实例
_db_manager: Optional[DatabaseConnectionManager] = None


def get_database_manager() -> DatabaseConnectionManager:
    """获取数据库连接管理器实例"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseConnectionManager()
        # 初始化数据库表
        try:
            _db_manager.init_taosha_db_tables()
        except Exception as e:
            logger.warning(f"数据库表初始化失败，但继续运行: {e}")
    return _db_manager


# 便捷函数
def get_db_session():
    """获取数据库会话的便捷函数"""
    return SessionLocal()


@contextmanager
def get_db():
    """获取数据库会话的上下文管理器"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"数据库事务失败: {e}")
        raise
    finally:
        db.close()


# 数据库操作便捷函数
def execute_query(query: str, params: tuple = None, fetch: str = "all") -> Optional[Any]:
    """执行查询的便捷函数"""
    return get_database_manager().execute_query(query, params, fetch)


def execute_insert(table: str, data: Dict[str, Any]) -> int:
    """执行插入操作的便捷函数"""
    columns = list(data.keys())
    values = list(data.values())
    placeholders = ", ".join(["%s"] if get_database_manager().get_taosha_db_config()["type"] == "mysql" else ["?"] * len(columns))

    query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
    return get_database_manager().execute_query(query, tuple(values), fetch="lastrowid")


def execute_update(table: str, data: Dict[str, Any], where_clause: str, where_params: tuple = None) -> int:
    """执行更新操作的便捷函数"""
    set_clauses = [f"{k} = %s" if get_database_manager().get_taosha_db_config()["type"] == "mysql" else f"{k} = ?" for k in data.keys()]
    query = f"UPDATE {table} SET {', '.join(set_clauses)} WHERE {where_clause}"

    params = list(data.values()) + list(where_params or ())
    get_database_manager().execute_query(query, tuple(params))
    return 0  # 返回影响的行数（简化版本）


def execute_delete(table: str, where_clause: str, where_params: tuple = None) -> int:
    """执行删除操作的便捷函数"""
    query = f"DELETE FROM {table} WHERE {where_clause}"
    get_database_manager().execute_query(query, where_params)
    return 0  # 返回影响的行数（简化版本）