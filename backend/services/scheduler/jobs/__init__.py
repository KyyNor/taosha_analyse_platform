"""
定时任务集合
每个业务模块的定时任务都在这里注册
"""

from .offline_wide_table_job import sync_all_wide_tables_job
from .realtime_indicator_job import generate_realtime_wide_table_job
from .metadata_sync_job import metadata_sync_job
from .fine_report_sync_job import fine_report_sync_job
from .vector_training_job import vector_training_job
from .postgres_data_cleanup_job import postgres_data_cleanup_job

__all__ = [
    'sync_all_wide_tables_job',
    'generate_realtime_wide_table_job',
    'metadata_sync_job',
    'fine_report_sync_job',
    'vector_training_job',
    'postgres_data_cleanup_job',
]
