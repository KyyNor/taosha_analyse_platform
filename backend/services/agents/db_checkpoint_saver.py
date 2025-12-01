"""
LangGraph 状态持久化服务
"""
from contextlib import asynccontextmanager
import os
import urllib.parse

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.checkpoint.mysql.aio import AIOMySQLSaver

from utils.config import settings
from utils.logger import logger

@asynccontextmanager
async def get_checkpoint_saver_context():
    """获取检查点保存器的上下文管理器"""
    db_type = getattr(settings, 'taosha_db_type', 'sqlite')

    try:
        if db_type == 'sqlite':
            db_path = getattr(settings, 'taosha_db_sqlite_path', './database/metadata.db')
            # 确保目录存在
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            
            # AsyncSqliteSaver.from_conn_string 是一个异步上下文管理器
            async with AsyncSqliteSaver.from_conn_string(db_path) as saver:
                logger.info(f"Initialized SQLite Checkpoint Saver: {db_path}")
                yield saver
                
        elif db_type == 'mysql':
            host = getattr(settings, 'taosha_db_mysql_host', 'localhost')
            port = getattr(settings, 'taosha_db_mysql_port', 3306)
            database = getattr(settings, 'taosha_db_mysql_database', 'taosha')
            user = getattr(settings, 'taosha_db_mysql_user', 'root')
            password = getattr(settings, 'taosha_db_mysql_password', '')
            charset = getattr(settings, 'taosha_db_mysql_charset', 'utf8mb4')
            
            # 构建连接字符串
            encoded_password = urllib.parse.quote_plus(password)
            conn_string = f"mysql://{user}:{encoded_password}@{host}:{port}/{database}?charset={charset}"
            
            async with AIOMySQLSaver.from_conn_string(conn_string) as saver:
                logger.info(f"Initialized MySQL Checkpoint Saver: {host}:{port}/{database}")
                yield saver
                
        else:
            raise ValueError(f"不支持的数据库类型: {db_type}")
            
    except Exception as e:
        logger.error(f"Failed to initialize checkpoint saver: {e}")
        raise