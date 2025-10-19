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

    def update_task_progress(self, task_id: str, progress_data: Dict[str, Any]) -> None:
        """
        更新任务进度信息

        Args:
            task_id: 任务ID
            progress_data: 进度更新数据
        """
        with self._lock:
            if task_id in self.cache:
                self.cache[task_id].update(progress_data)

    def add_step_log(self, task_id: str, step_log: Dict[str, Any]) -> None:
        """
        添加步骤日志到任务状态

        Args:
            task_id: 任务ID
            step_log: 步骤日志
        """
        with self._lock:
            if task_id in self.cache:
                if "logs" not in self.cache[task_id]:
                    self.cache[task_id]["logs"] = []
                self.cache[task_id]["logs"].append(step_log)

    def clear_task(self, task_id: str) -> None:
        """
        清除任务缓存

        Args:
            task_id: 任务ID
        """
        with self._lock:
            self.cache.pop(task_id, None)

    def get_all_tasks(self) -> List[str]:
        """
        获取所有缓存中的任务ID

        Returns:
            任务ID列表
        """
        with self._lock:
            return list(self.cache.keys())

    def size(self) -> int:
        """
        获取缓存大小

        Returns:
            缓存中的条目数量
        """
        with self._lock:
            return len(self.cache)

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