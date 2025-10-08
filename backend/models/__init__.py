"""
数据模型包初始化
"""
# 导入 Base 类
from utils.database import Base

# 导入所有模型，确保它们被注册
from . import metadata_models
from . import nlquery_models  
from . import system_models

__all__ = [
    "Base",
    "metadata_models",
    "nlquery_models", 
    "system_models"
]