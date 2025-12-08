"""
统一的项目级调度服务模块

提供全局单例调度器，管理所有定时任务
"""

from .scheduler_service import scheduler_service

__all__ = ['scheduler_service']
