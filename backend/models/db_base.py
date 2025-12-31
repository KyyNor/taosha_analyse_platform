"""
SQLAlchemy基础配置
改进MySQL连接超时问题
"""

from sqlalchemy import create_engine, MetaData
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
        logger.info("数据库表创建成功")
    except Exception as e:
        logger.error(f"数据库表创建失败: {e}")
        raise

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
