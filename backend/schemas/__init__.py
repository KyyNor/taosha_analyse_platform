"""
Pydantic Schemas 包初始化
"""
from .base import BaseResponse, PaginatedResponse, BaseSchema
from .metadata_schemas import *
from .nlquery_schemas import *
from .system_schemas import *

__all__ = [
    # 基础
    "BaseResponse",
    "PaginatedResponse", 
    "BaseSchema",
    
    # 元数据相关
    "DataThemeCreate",
    "DataThemeUpdate",
    "DataThemeResponse",
    "TableCreate",
    "TableUpdate", 
    "TableResponse",
    "FieldCreate",
    "FieldUpdate",
    "FieldResponse",
    "GlossaryCreate",
    "GlossaryUpdate",
    "GlossaryResponse",
    
    # 查询相关
    "QueryTaskCreate",
    "QueryTaskResponse",
    "QueryHistoryResponse",
    "QueryFavoriteCreate",
    "QueryFavoriteResponse",
    
    # 系统相关
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "RoleCreate", 
    "RoleResponse",
    "PermissionResponse",
]