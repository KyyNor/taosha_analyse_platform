"""
统一的项目级调度服务
管理所有定时任务的中心调度器
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from utils.logger import logger
from utils.config import settings
from typing import Optional, Callable


class SchedulerService:
    """
    全局调度服务 - 统一管理所有定时任务

    特点:
    - 单例模式，全局唯一实例
    - 支持多种触发器 (interval, cron)
    - 统一的启动和关闭管理
    - 防止重复启动
    """

    _instance: Optional['SchedulerService'] = None

    def __new__(cls):
        """单例模式实现"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """初始化调度器（仅执行一次）"""
        if self._initialized:
            return

        self.scheduler = AsyncIOScheduler()
        self._started = False
        self._initialized = True
        logger.debug("全局调度服务已初始化")

    def add_interval_job(
        self,
        func: Callable,
        seconds: int,
        job_id: str,
        job_name: str,
        replace_existing: bool = True
    ):
        """
        添加间隔触发的定时任务

        Args:
            func: 要执行的函数（必须是async函数）
            seconds: 执行间隔（秒）
            job_id: 任务唯一标识
            job_name: 任务名称（用于日志）
            replace_existing: 是否替换同ID的现有任务
        """
        try:
            self.scheduler.add_job(
                func,
                trigger=IntervalTrigger(seconds=seconds),
                id=job_id,
                name=job_name,
                replace_existing=replace_existing
            )
            logger.info(f"已添加定时任务: {job_name} (ID: {job_id}, 间隔: {seconds}秒)")
        except Exception as e:
            logger.error(f"添加定时任务失败: {job_name}, error={e}", exc_info=True)

    def add_cron_job(
        self,
        func: Callable,
        cron: str,
        job_id: str,
        job_name: str,
        replace_existing: bool = True
    ):
        """
        添加Cron表达式触发的定时任务

        Args:
            func: 要执行的函数（必须是async函数）
            cron: Cron表达式 (例如: "0 2 * * *" - 每天凌晨2点)
            job_id: 任务唯一标识
            job_name: 任务名称（用于日志）
            replace_existing: 是否替换同ID的现有任务
        """
        try:
            # Cron格式: "秒 分 时 日 月 周"
            # APScheduler格式: second, minute, hour, day, month, day_of_week
            parts = cron.split()
            if len(parts) == 5:
                # 标准Cron (无秒): "分 时 日 月 周"
                minute, hour, day, month, day_of_week = parts
                second = "0"
            elif len(parts) == 6:
                # 扩展Cron (有秒): "秒 分 时 日 月 周"
                second, minute, hour, day, month, day_of_week = parts
            else:
                raise ValueError(f"无效的Cron表达式: {cron}")

            self.scheduler.add_job(
                func,
                trigger=CronTrigger(
                    second=second,
                    minute=minute,
                    hour=hour,
                    day=day,
                    month=month,
                    day_of_week=day_of_week
                ),
                id=job_id,
                name=job_name,
                replace_existing=replace_existing
            )
            logger.info(f"已添加Cron任务: {job_name} (ID: {job_id}, Cron: {cron})")
        except Exception as e:
            logger.error(f"添加Cron任务失败: {job_name}, error={e}", exc_info=True)

    def remove_job(self, job_id: str):
        """
        移除指定任务

        Args:
            job_id: 任务ID
        """
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"已移除任务: {job_id}")
        except Exception as e:
            logger.warning(f"移除任务失败: {job_id}, error={e}")

    def start(self):
        """启动调度器"""
        if self._started:
            logger.warning("调度器已经启动，跳过重复启动")
            return

        try:
            self.scheduler.start()
            self._started = True

            # 打印所有已注册的任务
            jobs = self.scheduler.get_jobs()
            logger.info(f"=== 全局调度器已启动，共{len(jobs)}个任务 ===")
            for job in jobs:
                logger.info(f"  - {job.name} (ID: {job.id})")
        except Exception as e:
            logger.error(f"调度器启动失败: {e}", exc_info=True)
            raise

    def shutdown(self, wait: bool = True):
        """
        关闭调度器

        Args:
            wait: 是否等待所有任务完成
        """
        if not self._started:
            logger.debug("调度器未启动，无需关闭")
            return

        try:
            self.scheduler.shutdown(wait=wait)
            self._started = False
            logger.info("全局调度器已关闭")
        except Exception as e:
            logger.error(f"关闭调度器失败: {e}", exc_info=True)

    def get_jobs(self):
        """获取所有任务列表"""
        return self.scheduler.get_jobs()

    def is_running(self) -> bool:
        """检查调度器是否运行中"""
        return self._started


# 全局单例实例
scheduler_service = SchedulerService()
