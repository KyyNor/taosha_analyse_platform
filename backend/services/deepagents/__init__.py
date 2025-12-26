"""
DeepAgents 服务模块
提供数据分析任务队列管理和执行功能
"""

from services.deepagents.deepagents_service import (
    DeepAgentsTaskExecutor,
    get_task_executor,
)

__all__ = [
    "DeepAgentsTaskExecutor",
    "get_task_executor",
]
