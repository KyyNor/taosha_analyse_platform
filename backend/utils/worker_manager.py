"""
Worker管理器 - 基于文件锁的Worker序号分配机制

解决PID取余冲突问题：
- 问题：多个worker的PID取余可能相同（如111%2=1, 119%2=1）
- 方案：使用文件锁保护的注册表分配唯一序号
- 特性：心跳检测、自动清理死亡worker、序号复用
"""
import os
import json
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, Dict, List

from filelock import FileLock, Timeout

from utils.logger import logger


@dataclass
class WorkerInfo:
    """Worker信息"""
    worker_index: int           # Worker序号
    pid: int                    # 进程ID
    hostname: str               # 主机名
    start_time: str             # 启动时间 (ISO格式)
    heartbeat: str              # 最后心跳时间 (ISO格式)
    status: str = "active"      # 状态: active, stale, dead

    def to_dict(self) -> dict:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "WorkerInfo":
        """从字典创建实例"""
        return cls(**data)


class WorkerRegistry:
    """Worker注册表管理器"""

    # 版本号（用于注册表格式变更）
    VERSION = "1.0"

    # 心跳超时时间（秒）- 3次心跳未更新视为死亡
    HEARTBEAT_TIMEOUT = 90

    # 注册表锁超时时间（秒）
    LOCK_TIMEOUT = 10

    def __init__(self, registry_dir: Path, worker_count: int):
        """初始化注册表

        Args:
            registry_dir: 注册表目录路径
            worker_count: Worker总数
        """
        self.registry_dir = registry_dir
        self.worker_count = worker_count
        self.registry_file = registry_dir / "registry.json"
        self.lock_file = registry_dir / "registry.lock"

        # 确保目录存在
        self.registry_dir.mkdir(parents=True, exist_ok=True)

    def _get_lock(self) -> FileLock:
        """获取注册表锁"""
        return FileLock(str(self.lock_file), timeout=self.LOCK_TIMEOUT)

    def _load_registry(self) -> dict:
        """加载注册表

        Returns:
            注册表字典，如果不存在则返回空注册表
        """
        if not self.registry_file.exists():
            # 创建新注册表
            return {
                "version": self.VERSION,
                "worker_count": self.worker_count,
                "generation": 0,
                "last_updated": datetime.now().isoformat(),
                "workers": {}
            }

        try:
            with open(self.registry_file, "r", encoding="utf-8") as f:
                registry = json.load(f)

            # 验证版本兼容性
            if registry.get("version") != self.VERSION:
                logger.warning(f"注册表版本不匹配: {registry.get('version')} != {self.VERSION}")

            return registry
        except Exception as e:
            logger.error(f"加载注册表失败: {e}，将创建新注册表")
            return {
                "version": self.VERSION,
                "worker_count": self.worker_count,
                "generation": 0,
                "last_updated": datetime.now().isoformat(),
                "workers": {}
            }

    def _save_registry(self, registry: dict):
        """保存注册表

        Args:
            registry: 注册表字典
        """
        registry["last_updated"] = datetime.now().isoformat()
        try:
            with open(self.registry_file, "w", encoding="utf-8") as f:
                json.dump(registry, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存注册表失败: {e}", exc_info=True)
            raise

    def _cleanup_stale_workers(self, registry: dict):
        """清理超时的死亡worker

        Args:
            registry: 注册表字典（会被就地修改）
        """
        workers = registry.get("workers", {})
        now = datetime.now()
        stale_workers = []

        for worker_index, worker_data in workers.items():
            try:
                heartbeat_time = datetime.fromisoformat(worker_data["heartbeat"])
                time_diff = (now - heartbeat_time).total_seconds()

                if time_diff > self.HEARTBEAT_TIMEOUT:
                    stale_workers.append(worker_index)
                    logger.info(
                        f"发现死亡worker: {worker_index} (PID:{worker_data['pid']}, "
                        f"最后心跳: {time_diff:.0f}秒前)"
                    )
            except Exception as e:
                logger.error(f"解析worker心跳时间失败: {e}")
                stale_workers.append(worker_index)

        # 移除死亡worker
        for worker_index in stale_workers:
            worker_data = workers.pop(worker_index)
            # 删除worker元数据文件
            worker_file = self.registry_dir / f"worker_{worker_index}.json"
            try:
                if worker_file.exists():
                    worker_file.remove()
            except Exception as e:
                logger.warning(f"删除worker文件失败: {e}")

        if stale_workers:
            registry["generation"] = registry.get("generation", 0) + 1
            logger.info(f"已清理 {len(stale_workers)} 个死亡worker，代次: {registry['generation']}")

    def register_worker(self, pid: int) -> int:
        """注册worker并分配序号

        Args:
            pid: 进程ID

        Returns:
            分配的worker序号

        Raises:
            Timeout: 获取锁超时
            Exception: 注册失败
        """
        import socket
        hostname = socket.gethostname()
        now = datetime.now()

        try:
            with self._get_lock():
                # 加载注册表
                registry = self._load_registry()

                # 清理死亡worker
                self._cleanup_stale_workers(registry)

                workers = registry.get("workers", {})

                # 查找空闲序号（优先使用之前的序号）
                assigned_index = None
                for i in range(self.worker_count):
                    if str(i) not in workers:
                        assigned_index = i
                        break

                if assigned_index is None:
                    raise Exception(f"所有worker序号都已占用（worker_count={self.worker_count}）")

                # 创建worker信息
                worker_info = WorkerInfo(
                    worker_index=assigned_index,
                    pid=pid,
                    hostname=hostname,
                    start_time=now.isoformat(),
                    heartbeat=now.isoformat(),
                    status="active"
                )

                # 更新注册表
                workers[str(assigned_index)] = worker_info.to_dict()
                registry["workers"] = workers
                registry["worker_count"] = self.worker_count
                self._save_registry(registry)

                # 保存worker元数据文件
                worker_file = self.registry_dir / f"worker_{assigned_index}.json"
                with open(worker_file, "w", encoding="utf-8") as f:
                    json.dump(worker_info.to_dict(), f, indent=2, ensure_ascii=False)

                logger.info(
                    f"[Worker注册] PID={pid} 成功注册为 Worker {assigned_index}/{self.worker_count} "
                    f"(hostname={hostname})"
                )

                return assigned_index

        except Timeout:
            logger.error(f"[Worker注册] PID={pid} 获取注册表锁超时")
            raise
        except Exception as e:
            logger.error(f"[Worker注册] PID={pid} 注册失败: {e}", exc_info=True)
            raise

    def heartbeat(self, worker_index: int, pid: int):
        """更新worker心跳

        Args:
            worker_index: Worker序号
            pid: 进程ID
        """
        try:
            # 不使用锁，仅更新时间戳和worker文件
            worker_file = self.registry_dir / f"worker_{worker_index}.json"

            if not worker_file.exists():
                logger.warning(f"[Worker心跳] Worker {worker_index} 文件不存在")
                return

            # 读取worker信息
            with open(worker_file, "r", encoding="utf-8") as f:
                worker_info = WorkerInfo.from_dict(json.load(f))

            # 验证PID匹配
            if worker_info.pid != pid:
                logger.warning(
                    f"[Worker心跳] Worker {worker_index} PID不匹配: "
                    f"{worker_info.pid} != {pid}"
                )
                return

            # 更新心跳时间
            worker_info.heartbeat = datetime.now().isoformat()

            # 写入worker文件
            with open(worker_file, "w", encoding="utf-8") as f:
                json.dump(worker_info.to_dict(), f, indent=2, ensure_ascii=False)

            # 同时更新注册表（无需锁，原子写入）
            try:
                with self._get_lock():
                    registry = self._load_registry()
                    workers = registry.get("workers", {})
                    if str(worker_index) in workers:
                        workers[str(worker_index)]["heartbeat"] = worker_info.heartbeat
                        workers[str(worker_index)]["status"] = "active"
                        self._save_registry(registry)
            except Exception as e:
                # 注册表更新失败不影响心跳（已更新worker文件）
                logger.debug(f"[Worker心跳] 更新注册表失败: {e}")

        except Exception as e:
            logger.error(f"[Worker心跳] 更新失败: {e}", exc_info=True)

    def unregister_worker(self, worker_index: int, pid: int):
        """注销worker

        Args:
            worker_index: Worker序号
            pid: 进程ID
        """
        try:
            with self._get_lock():
                registry = self._load_registry()
                workers = registry.get("workers", {})

                if str(worker_index) not in workers:
                    logger.warning(f"[Worker注销] Worker {worker_index} 不在注册表中")
                    return

                # 验证PID匹配
                if workers[str(worker_index)]["pid"] != pid:
                    logger.warning(
                        f"[Worker注销] Worker {worker_index} PID不匹配: "
                        f"{workers[str(worker_index)]['pid']} != {pid}"
                    )
                    return

                # 从注册表移除
                workers.pop(str(worker_index))
                registry["workers"] = workers
                registry["generation"] = registry.get("generation", 0) + 1
                self._save_registry(registry)

                # 删除worker文件
                worker_file = self.registry_dir / f"worker_{worker_index}.json"
                if worker_file.exists():
                    worker_file.remove()

                logger.info(f"[Worker注销] Worker {worker_index}/{self.worker_count} (PID={pid})")

        except Exception as e:
            logger.error(f"[Worker注销] 注销失败: {e}", exc_info=True)

    def get_registry_info(self) -> dict:
        """获取注册表信息（用于调试）

        Returns:
            注册表信息字典
        """
        try:
            with self._get_lock():
                registry = self._load_registry()
                return {
                    "version": registry.get("version"),
                    "worker_count": registry.get("worker_count"),
                    "generation": registry.get("generation"),
                    "last_updated": registry.get("last_updated"),
                    "workers": registry.get("workers", {})
                }
        except Exception as e:
            logger.error(f"获取注册表信息失败: {e}", exc_info=True)
            return {}


class WorkerManager:
    """Worker管理器单例

    负责启动心跳线程，定期更新worker存活状态
    """

    _instance: Optional["WorkerManager"] = None
    _lock = threading.Lock()

    # 心跳间隔（秒）
    HEARTBEAT_INTERVAL = 30

    def __init__(self):
        """私有构造函数（使用get_worker_manager()获取实例）"""
        self.registry: Optional[WorkerRegistry] = None
        self.worker_index: Optional[int] = None
        self.pid: Optional[int] = None
        self.worker_count: Optional[int] = None
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._initialized = False

    @classmethod
    def get_instance(cls) -> "WorkerManager":
        """获取WorkerManager单例实例

        Returns:
            WorkerManager实例
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def initialize(self, worker_count: int) -> int:
        """初始化WorkerManager并注册当前worker

        Args:
            worker_count: Worker总数

        Returns:
            分配的worker序号

        Raises:
            Exception: 初始化失败
        """
        if self._initialized:
            return self.worker_index

        try:
            self.pid = os.getpid()
            self.worker_count = worker_count

            # 确定注册表目录（backend/.worker_registry/）
            backend_dir = Path(__file__).parent.parent
            registry_dir = backend_dir / ".worker_registry"

            # 创建注册表
            self.registry = WorkerRegistry(
                registry_dir=registry_dir,
                worker_count=worker_count
            )

            # 注册当前worker
            self.worker_index = self.registry.register_worker(self.pid)

            # 启动心跳线程
            self._start_heartbeat_thread()

            self._initialized = True

            logger.info(
                f"[WorkerManager] 初始化完成: Worker {self.worker_index}/{worker_count} "
                f"(PID={self.pid})"
            )

            return self.worker_index

        except Exception as e:
            logger.error(f"[WorkerManager] 初始化失败: {e}", exc_info=True)
            raise

    def _start_heartbeat_thread(self):
        """启动心跳线程"""
        self._stop_event.clear()
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            daemon=True,
            name=f"WorkerHeartbeat-{self.worker_index}"
        )
        self._heartbeat_thread.start()
        logger.info(f"[Worker心跳] 心跳线程已启动 (间隔={self.HEARTBEAT_INTERVAL}秒)")

    def _heartbeat_loop(self):
        """心跳循环（运行在独立线程中）"""
        while not self._stop_event.is_set():
            try:
                # 等待间隔或停止事件
                self._stop_event.wait(timeout=self.HEARTBEAT_INTERVAL)

                if self._stop_event.is_set():
                    break

                # 更新心跳
                if self.registry and self.worker_index is not None and self.pid is not None:
                    self.registry.heartbeat(self.worker_index, self.pid)

            except Exception as e:
                logger.error(f"[Worker心跳] 心跳更新失败: {e}", exc_info=True)

        logger.info(f"[Worker心跳] 心跳线程已停止 (Worker {self.worker_index})")

    def shutdown(self):
        """关闭WorkerManager"""
        if not self._initialized:
            return

        try:
            # 停止心跳线程
            self._stop_event.set()
            if self._heartbeat_thread and self._heartbeat_thread.is_alive():
                self._heartbeat_thread.join(timeout=5)

            # 注销worker
            if self.registry and self.worker_index is not None and self.pid is not None:
                self.registry.unregister_worker(self.worker_index, self.pid)

            logger.info(
                f"[WorkerManager] 已关闭: Worker {self.worker_index}/{self.worker_count} "
                f"(PID={self.pid})"
            )

        except Exception as e:
            logger.error(f"[WorkerManager] 关闭失败: {e}", exc_info=True)
        finally:
            self._initialized = False


# 全局访问函数
def get_worker_manager() -> WorkerManager:
    """获取WorkerManager单例实例

    Returns:
        WorkerManager实例
    """
    return WorkerManager.get_instance()
