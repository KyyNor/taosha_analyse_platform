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
    relation_id: str = ""


class ColumnMetadataUpdate(BaseModel):
    type: Optional[str] = None
    comment: Optional[str] = None
    is_available: Optional[int] = None
    business_type: Optional[str] = None
    relation_id: Optional[str] = None


class GlossaryTermRequest(BaseModel):
    term: str
    definition: str = ""
    sql_expression: str = ""
    category: str = ""
    aliases: List[str] = []


class GlossaryTermUpdate(BaseModel):
    term: Optional[str] = None
    definition: Optional[str] = None
    sql_expression: Optional[str] = None
    category: Optional[str] = None


class RelationFieldConfigRequest(BaseModel):
    relation_family: str
    relation_subfamily: str
    relation_desc: str = ""


class RelationFieldConfigUpdate(BaseModel):
    relation_family: Optional[str] = None
    relation_subfamily: Optional[str] = None
    relation_desc: Optional[str] = None


# === 查询历史相关模型 ===
# 注意：查询历史相关模型已迁移到 service_models.TaskState，以实现数据结构复用
