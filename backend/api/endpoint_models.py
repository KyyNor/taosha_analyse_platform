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
    selected_theme_id: Optional[int] = Field(None, description="选中的数据主题ID")
    selected_table_ids: Optional[List[int]] = Field(None, description="选中的数据表ID列表")

class ClarificationInput(BaseModel):
    clarification_input: str

# 数据模型
class TableMetadataRequest(BaseModel):
    name: str
    comment: str = ""
    remark: str = ""
    is_available: int = 0


class TableMetadataUpdate(BaseModel):
    comment: Optional[str] = None
    remark: Optional[str] = None
    is_available: Optional[int] = None


class ColumnMetadataRequest(BaseModel):
    table_id: int
    name: str
    type: str
    comment: str = ""
    remark: str = ""
    is_available: int = 0
    business_type: str = ""
    relation_config_id: Optional[int] = None


class ColumnMetadataUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    comment: Optional[str] = None
    remark: Optional[str] = None
    is_available: Optional[int] = None
    business_type: Optional[str] = None
    relation_config_id: Optional[int] = None


class GlossaryTermRequest(BaseModel):
    name: str
    type: str  # concept/sql_qa/dict_mapping
    content: Dict[str, Any]
    creator: str = ""
    is_basic: bool = False  # 添加 is_basic 字段，默认为 False


class GlossaryTermUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    content: Optional[Dict[str, Any]] = None
    is_basic: Optional[bool] = None  # 添加 is_basic 字段


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




class BatchUpdateRequest(BaseModel):
    """批量更新表和字段请求"""
    table: Dict[str, Any] = Field(default=None, description="表更新数据")
    columns: List[Dict[str, Any]] = Field(default_factory=list, description="字段更新列表")


class BatchUpdateResult(BaseModel):
    """批量更新结果"""
    success_count: int = Field(..., description="成功操作数量")
    error_count: int = Field(..., description="失败操作数量")
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="错误详情")


class FineReportRequest(BaseModel):
    """FineReport报表创建请求"""
    report_name: str = Field(..., description="报表名称", min_length=1, max_length=255)
    report_cpt_path: str = Field(..., description="cpt文件路径", min_length=1)
    report_type: str = Field(..., description="报表类型: summary=汇总表, detail=明细表")
    report_design_address: str = Field(..., description="设计器地址", min_length=1, max_length=255)
    department_id: Optional[int] = Field(None, description="所属部门ID")
    description: str = Field("", description="报表说明")
    usage_scenario: str = Field("", description="适用场景")
    is_available: int = Field(0, description="是否可用: 0=可用, 1=不可用")


class FineReportUpdate(BaseModel):
    """FineReport报表更新请求"""
    report_name: Optional[str] = Field(None, description="报表名称", min_length=1, max_length=255)
    report_cpt_path: Optional[str] = Field(None, description="cpt文件路径", min_length=1)
    report_type: Optional[str] = Field(None, description="报表类型: summary=汇总表, detail=明细表")
    report_design_address: Optional[str] = Field(None, description="设计器地址", min_length=1, max_length=255)
    department_id: Optional[int] = Field(None, description="所属部门ID")
    description: Optional[str] = Field(None, description="报表说明")
    usage_scenario: Optional[str] = Field(None, description="适用场景")
    is_available: Optional[int] = Field(None, description="是否可用: 0=可用, 1=不可用")


