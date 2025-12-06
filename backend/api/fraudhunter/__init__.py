"""
FraudHunter API路由模块
"""

from .indicator_task_routes import router as indicator_task_router
from .indicator_routes import router as indicator_router
from .dry_run_task_routes import router as task_router
from .wide_table_routes import router as wide_table_router

__all__ = [
    'indicator_task_router',
    'indicator_router',
    'task_router',
    'wide_table_router',
]
