"""
任务状态缓存管理器
用于OperationTracker的缓存管理，支持WebSocket高效读取
"""

from cachetools import TTLCache
from typing import Optional, Dict, Any, List
from datetime import datetime
import threading

from ..service_models import TaskState, BaseNodeLog


class TrackerCache:
    """任务状态缓存管理器"""

    def __init__(self, maxsize: int = 1000, ttl: int = 3600):
        """
        初始化缓存管理器

        Args:
            maxsize: 缓存最大条目数
            ttl: 缓存过期时间（秒）
        """
        self.cache = TTLCache(maxsize=maxsize, ttl=ttl)
        self._lock = threading.RLock()

    def get_task_state(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务状态

        Args:
            task_id: 任务ID

        Returns:
            任务状态字典，如果不存在则返回None
        """
        with self._lock:
            return self.cache.get(task_id)

    def set_task_state(self, task_id: str, state: Dict[str, Any]) -> None:
        """
        设置任务状态

        Args:
            task_id: 任务ID
            state: 任务状态字典
        """
        with self._lock:
            self.cache[task_id] = state

    def cleanup_expired(self) -> int:
        """
        清理过期缓存条目

        Returns:
            清理的条目数量
        """
        # TTLCache会自动清理过期条目，这里只是触发清理
        with self._lock:
            # 访问所有键来触发过期检查
            keys = list(self.cache.keys())
            return len(keys) - len(self.cache)


# 全局缓存实例
tracker_cache = TrackerCache()