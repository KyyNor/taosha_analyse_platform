"""
服务层包初始化
"""
from .metadata_service import MetadataService, get_metadata_service

__all__ = [
    "MetadataService",
    "get_metadata_service",
]