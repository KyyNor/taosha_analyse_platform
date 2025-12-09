"""
FraudHunter宽表版本管理服务模块
"""

from .version_manager import WideTableVersionManager
from .sync_service import WideTableSyncService

__all__ = [
    'WideTableVersionManager',
    'WideTableSyncService',
]
