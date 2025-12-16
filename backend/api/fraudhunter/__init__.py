"""
FraudHunter API路由模块
"""

from .indicator_task_routes import router as indicator_task_router
from .indicator_routes import router as indicator_router
from .model_routes import router as model_router, risk_control_model_router
from .dry_run_task_routes import router as task_router
from .wide_table_routes import router as wide_table_router
from .alert_control_record_routes import router as alert_control_record_router
from .system_config_routes import router as system_config_router

__all__ = [
    'indicator_task_router',
    'indicator_router',
    'task_router',
    'model_router',
    'risk_control_model_router',
    'wide_table_router',
    'alert_control_record_router',
    'system_config_router',
]
