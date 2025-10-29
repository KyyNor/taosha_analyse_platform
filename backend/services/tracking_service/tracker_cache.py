"""
任务状态缓存管理器
用于OperationTracker的缓存管理，支持WebSocket高效读取
"""
import os

from diskcache import FanoutCache
from typing import Optional, Dict, Any, List
from datetime import datetime
from utils.logger import logger
from utils.config import settings


class TrackerCache:
    """任务状态缓存管理器"""

    def __init__(self, maxsize: int = 1*1024*1024*1024):
        """
        初始化缓存管理器

        Args:
            maxsize: 最大缓存空间 1*1024*1024*1024 为1GB
        """
        self.cache = FanoutCache(
            directory=f"{settings.disk_cache_path}{os.sep}tracker_cache",
            shards=8,
            size_limit=maxsize,
        )

    def get_task_state(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务状态

        Args:
            task_id: 任务ID

        Returns:
            任务状态字典，如果不存在则返回None
        """
        return self.cache.get(task_id)

    def set_task_state(self, task_id: str, state: Dict[str, Any]) -> None:
        """
        设置任务状态（自动添加update_time时间戳）

        Args:
            task_id: 任务ID
            state: 任务状态字典
        """
        # 添加或更新update_time时间戳（用于长轮询增量查询）
        state_copy = state.copy()
        state_copy['update_time'] = datetime.now().isoformat()
        self.cache.set(task_id, state_copy)
        logger.debug(f"缓存已更新: task_id={task_id}, update_time={state_copy['update_time']}")


# 全局缓存实例
tracker_cache = TrackerCache()