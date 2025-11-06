"""
Excel文件解析工具
用于解析FineReport下载的Excel文件并转换为结构化数据
"""
import os
import pandas as pd
from typing import Dict, Any, List, Optional
from pathlib import Path
from loguru import logger


def clean_excel_file(file_path: str) -> bool:
    """
    清理Excel文件

    Args:
        file_path: 文件路径

    Returns:
        是否删除成功
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"已删除Excel文件: {file_path}")
            return True
        return False
    except Exception as e:
        logger.error(f"删除Excel文件失败 {file_path}: {e}")
        return False


def ensure_download_dir(download_path: str) -> bool:
    """
    确保下载目录存在

    Args:
        download_path: 下载目录路径

    Returns:
        目录是否存在或创建成功
    """
    try:
        Path(download_path).mkdir(parents=True, exist_ok=True)
        logger.debug(f"下载目录已准备: {download_path}")
        return True
    except Exception as e:
        logger.error(f"创建下载目录失败 {download_path}: {e}")
        return False