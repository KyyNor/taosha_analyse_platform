"""
FraudHunter API路由模块
"""

from .indicator_task_routes import router as indicator_task_router
from .indicator_routes import router as indicator_router
from .task_routes import router as task_router
from .model_routes import router as model_router, risk_control_model_router

__all__ = [
    'indicator_task_router',
    'indicator_router',
    'task_router',
    'model_router',
    'risk_control_model_router',
]
