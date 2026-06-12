"""
SQLAlchemy基础配置
改进MySQL连接超时问题
"""

from sqlalchemy import create_engine, MetaData, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from typing import Generator
from utils.config import settings
from utils.logger import logger
import os

# 数据库连接配置
def get_database_url() -> str:
    """获取数据库连接URL"""
    db_type = getattr(settings, 'taosha_db_type', 'mysql')

    if db_type == 'mysql':
        host = getattr(settings, 'taosha_db_mysql_host', 'localhost')
        port = getattr(settings, 'taosha_db_mysql_port', 3306)
        database = getattr(settings, 'taosha_db_mysql_database', 'taosha')
        user = getattr(settings, 'taosha_db_mysql_user', 'root')
        password = getattr(settings, 'taosha_db_mysql_password', '')
        charset = getattr(settings, 'taosha_db_mysql_charset', 'utf8mb4')
        return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset={charset}"
    else:
        raise ValueError(f"不支持的数据库类型: {db_type}")

# 创建数据库引擎（改进配置）
engine = create_engine(
    get_database_url(),
    echo=getattr(settings, 'sql_debug', False),  # 是否打印SQL语句
    pool_pre_ping=True,  # 连接池预检查
    pool_recycle=7200,    # 连接回收时间（秒）- 改为2小时
    pool_size=10,         # 连接池大小
    max_overflow=20,      # 最大溢出连接数
    pool_timeout=30,      # 获取连接的超时时间
    # 添加MySQL特定参数
    connect_args={
        "connect_timeout": 180,
        "read_timeout": 600,
        "write_timeout": 600,
        "charset": "utf8mb4"
    }
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建声明基类
Base = declarative_base()

# 数据库依赖项
def get_db() -> Generator:
    """获取数据库会话的依赖函数（FastAPI依赖注入）

    在请求结束时自动提交事务，如有异常则回滚。
    这样所有API路由的数据修改都会被自动持久化。
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()  # 请求成功时提交事务
    except Exception:
        db.rollback()  # 异常时回滚
        logger.error(f"数据库事务回滚")
        raise
    finally:
        db.close()

# 上下文管理器
@contextmanager
def get_db_session():
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

def create_tables():
    """创建所有表"""
    try:
        Base.metadata.create_all(bind=engine)
        _apply_lightweight_migrations()
        logger.info("数据库表创建成功")
    except Exception as e:
        logger.error(f"数据库表创建失败: {e}")
        raise

def _apply_lightweight_migrations():
    """应用少量向后兼容的表结构补丁。

    项目当前没有 Alembic；create_all 不会修改既有表，所以新增字段需要在启动时补齐。
    """
    inspector = inspect(engine)
    table_names = inspector.get_table_names()

    with engine.begin() as connection:
        if "fraudhunter_dryrun_execution" in table_names:
            _migrate_dryrun_execution_table(connection, inspector)

        if "fraudhunter_model_definition" in table_names:
            _migrate_model_definition_table(connection, inspector)


def _migrate_dryrun_execution_table(connection, inspector):
    table_name = "fraudhunter_dryrun_execution"
    columns = {column["name"] for column in inspector.get_columns(table_name)}

    if "parent_execution_id" not in columns:
        connection.execute(text(
            "ALTER TABLE fraudhunter_dryrun_execution "
            "ADD COLUMN parent_execution_id VARCHAR(64) NULL COMMENT '父执行ID（批量任务关联子任务）'"
        ))
        logger.info("已为 fraudhunter_dryrun_execution 添加 parent_execution_id 字段")

    index_names = {index["name"] for index in inspector.get_indexes(table_name)}
    if "idx_fh_dryrun_parent_execution_id" not in index_names:
        connection.execute(text(
            "CREATE INDEX idx_fh_dryrun_parent_execution_id "
            "ON fraudhunter_dryrun_execution (parent_execution_id)"
        ))
        logger.info("已为 fraudhunter_dryrun_execution.parent_execution_id 添加索引")


def _migrate_model_definition_table(connection, inspector):
    table_name = "fraudhunter_model_definition"
    columns = {column["name"] for column in inspector.get_columns(table_name)}

    if "model_type" not in columns:
        connection.execute(text(
            "ALTER TABLE fraudhunter_model_definition "
            "ADD COLUMN model_type VARCHAR(16) NULL DEFAULT 'normal' COMMENT '模型类型：normal/prefix'"
        ))
        logger.info("已为 fraudhunter_model_definition 添加 model_type 字段")

    if "online_at" not in columns:
        connection.execute(text(
            "ALTER TABLE fraudhunter_model_definition "
            "ADD COLUMN online_at DATETIME NULL COMMENT '上线时间'"
        ))
        logger.info("已为 fraudhunter_model_definition 添加 online_at 字段")

    if "online_by" not in columns:
        connection.execute(text(
            "ALTER TABLE fraudhunter_model_definition "
            "ADD COLUMN online_by VARCHAR(64) NULL COMMENT '上线人'"
        ))
        logger.info("已为 fraudhunter_model_definition 添加 online_by 字段")

    index_names = {index["name"] for index in inspector.get_indexes(table_name)}
    if "idx_fh_model_type" not in index_names:
        connection.execute(text(
            "CREATE INDEX idx_fh_model_type ON fraudhunter_model_definition (model_type)"
        ))
        logger.info("已为 fraudhunter_model_definition.model_type 添加索引")

def drop_tables():
    """删除所有表"""
    try:
        Base.metadata.drop_all(bind=engine)
        logger.info("数据库表删除成功")
    except Exception as e:
        logger.error(f"数据库表删除失败: {e}")
        raise

def reset_database():
    """重置数据库（先删除再创建）"""
    try:
        drop_tables()
        create_tables()
        logger.info("数据库重置成功")
    except Exception as e:
        logger.error(f"数据库重置失败: {e}")
        raise
