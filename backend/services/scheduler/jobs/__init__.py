"""
定时任务集合
每个业务模块的定时任务都在这里注册
"""

from .offline_wide_table_job import sync_all_wide_tables_job
from .realtime_indicator_job import generate_realtime_wide_table_job

__all__ = [
    'sync_all_wide_tables_job',
    'generate_realtime_wide_table_job',
]
