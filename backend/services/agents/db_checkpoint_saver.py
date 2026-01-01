"""
LangGraph 状态持久化服务
"""
from contextlib import asynccontextmanager
import os
import urllib.parse

from langgraph.checkpoint.mysql.aio import AIOMySQLSaver

from utils.config import settings
from utils.logger import logger

@asynccontextmanager
async def get_checkpoint_saver_context():
    """获取检查点保存器的上下文管理器"""
    db_type = getattr(settings, 'taosha_db_type', 'mysql')

    try:
        if db_type == 'mysql':
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
                # 调用 setup 初始化数据库表（幂等操作）
                await saver.setup()
                logger.info(f"Initialized MySQL Checkpoint Saver: {host}:{port}/{database}")
                yield saver
                
        else:
            raise ValueError(f"不支持的数据库类型: {db_type}")
            
    except Exception as e:
        logger.error(f"Failed to initialize checkpoint saver: {e}")
        raise