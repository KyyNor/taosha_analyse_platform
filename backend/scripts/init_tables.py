#!/usr/bin/env python
"""
初始化训练相关表
"""

import sys
from pathlib import Path

# 添加backend目录到路径
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from models.db_base import create_tables
from utils.logger import logger


def init_tables():
    """初始化数据库表"""
    try:
        logger.info("开始初始化表...")
        create_tables()
        logger.info("表初始化成功！")
    except Exception as e:
        logger.error(f"初始化表失败: {e}")
        raise


if __name__ == "__main__":
    init_tables()
