"""
FraudHunter API路由模块
"""

from .indicator_group_routes import router as indicator_group_router
from .indicator_routes import router as indicator_router
from .task_routes import router as task_router

__all__ = [
    'indicator_group_router',
    'indicator_router',
    'task_router',
]
