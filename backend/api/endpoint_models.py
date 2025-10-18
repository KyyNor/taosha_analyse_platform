"""
API数据模型定义
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class QueryRequest(BaseModel):
    """查询请求模型"""
    query: str = Field(..., description="自然语言查询", min_length=1)
    flow_type: str = Field("fast", description="流程类型: fast=先验证后生成SQL, thorough=先生成SQL后验证")
    max_retries: int = Field(2, description="最大重试次数", ge=0, le=5)

# 数据模型
class TableMetadataRequest(BaseModel):
    name: str
    comment: str = ""
    is_available: int = 0


class TableMetadataUpdate(BaseModel):
    comment: Optional[str] = None
    is_available: Optional[int] = None


class ColumnMetadataRequest(BaseModel):
    table_name: str
    name: str
    type: str
    comment: str = ""
    is_available: int = 0
    business_type: str = ""
    relation_config_id: Optional[int] = None


class ColumnMetadataUpdate(BaseModel):
    type: Optional[str] = None
    comment: Optional[str] = None
    is_available: Optional[int] = None
    business_type: Optional[str] = None
    relation_config_id: Optional[int] = None


class GlossaryTermRequest(BaseModel):
    name: str
    type: str  # concept/sql_qa/dict_mapping
    content: Dict[str, Any]
    creator: str = ""


class GlossaryTermUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    content: Optional[Dict[str, Any]] = None


class RelationFieldConfigRequest(BaseModel):
    relation_family: str
    relation_subfamily: str
    relation_desc: str = ""


class RelationFieldConfigUpdate(BaseModel):
    relation_family: Optional[str] = None
    relation_subfamily: Optional[str] = None
    relation_desc: Optional[str] = None


class PromptTemplateRequest(BaseModel):
    name: str
    fields: List[str]
    template: str


class PromptTemplateUpdate(BaseModel):
    name: Optional[str] = None
    template: Optional[str] = None


class DataThemeRequest(BaseModel):
    theme_name: str = Field(..., description="主题名称", min_length=1)
    theme_description: str = Field("", description="主题描述")
    theme_type: str = Field("normal", description="主题类型: normal=一般主题, public=通用主题")
    department: str = Field("", description="关联部门")


class DataThemeUpdate(BaseModel):
    theme_name: Optional[str] = Field(None, description="主题名称", min_length=1)
    theme_description: Optional[str] = Field(None, description="主题描述")
    theme_type: Optional[str] = Field(None, description="主题类型: normal=一般主题, public=通用主题")
    department: Optional[str] = Field(None, description="关联部门")


class ThemeTableRelationRequest(BaseModel):
    table_id: int = Field(..., description="表ID")


# === 查询历史相关模型 ===
# 注意：查询历史相关模型已迁移到 service_models.TaskState，以实现数据结构复用
