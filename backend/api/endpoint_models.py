"""
API数据模型定义
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

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


# ==================== 知识库相关数据模型 ====================

class KnowledgeDocumentRequest(BaseModel):
    """知识文档创建请求"""
    title: str = Field(..., description="文档标题", min_length=1, max_length=255)
    source_type: str = Field(..., description="源类型: file=文件, text=文本, sql=SQL文件")
    source_path: Optional[str] = Field(None, description="文件路径（绝对路径）")
    raw_content: Optional[str] = Field(None, description="原始内容（文本输入时使用）")


class KnowledgeDocumentUpdate(BaseModel):
    """知识文档更新请求"""
    title: Optional[str] = Field(None, description="文档标题", min_length=1, max_length=255)
    processing_status: Optional[str] = Field(None, description="处理状态: pending, processed, failed")


class FragmentGenerationRequest(BaseModel):
    """片段生成请求"""
    document_id: int = Field(..., description="文档ID")
    fragment_count: int = Field(5, description="生成的片段数量", ge=1, le=20)


class TopicExtractionRequest(BaseModel):
    """主题提取请求"""
    extraction_theme: str = Field(..., description="提取主题", min_length=1, max_length=500)
    extraction_prompt: str = Field(..., description="提取逻辑描述", min_length=1)


class SaveFragmentsRequest(BaseModel):
    """保存选中片段请求"""
    fragment_ids: List[int] = Field(..., description="选中的片段ID列表")
    edited_contents: Optional[Dict[int, Dict[str, str]]] = Field(
        default_factory=dict,
        description="编辑后的片段内容，格式: {fragment_id: {title: xxx, content: xxx, summary: xxx}}"
    )


class FragmentUpdateRequest(BaseModel):
    """片段更新请求"""
    title: Optional[str] = Field(None, description="片段标题", min_length=1, max_length=255)
    content: Optional[str] = Field(None, description="片段内容")
    summary: Optional[str] = Field(None, description="简短摘要")
    is_modified: Optional[bool] = Field(None, description="是否被用户修改")


class FragmentData(BaseModel):
    """片段数据（用于生成和提取返回）"""
    id: Optional[int] = Field(None, description="片段ID（已保存的片段有ID）")
    title: str = Field(..., description="片段标题")
    content: str = Field(..., description="片段内容")
    summary: Optional[str] = Field(None, description="简短摘要")
    generation_method: str = Field(..., description="生成方式: auto, user_extraction, manual")
    extraction_theme: Optional[str] = Field(None, description="提取主题")
    is_modified: bool = Field(False, description="是否被修改")


class DocumentDetailResponse(BaseModel):
    """文档详情响应"""
    id: int
    title: str
    source_type: str
    source_path: Optional[str]
    raw_content: str
    file_size: Optional[int]
    content_hash: Optional[str]
    processing_status: str
    fragment_count: int
    created_at: datetime
    updated_at: datetime
    fragments: List[FragmentData] = Field(default_factory=list, description="文档的片段列表")


class CandidateFragmentsResponse(BaseModel):
    """候选片段响应（生成和提取）"""
    document_id: int
    fragments: List[FragmentData] = Field(..., description="候选片段列表")
    total_count: int = Field(..., description="总片段数")


class SaveFragmentsResponse(BaseModel):
    """保存片段响应"""
    saved_fragment_ids: List[int] = Field(..., description="保存的片段ID列表")
    saved_count: int = Field(..., description="保存的片段数量")
    document_id: int = Field(..., description="文档ID")



