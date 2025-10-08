"""
元数据相关的 Pydantic Schemas
"""
from pydantic import Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

from .base import (
    BaseSchema, BaseCreateSchema, BaseUpdateSchema, BaseResponseSchema,
    BaseListParams
)
from models.metadata_models import (
    UpdateMethodEnum, FieldTypeEnum, BusinessTypeEnum, 
    DesensitizationTypeEnum, TermTypeEnum
)


# ========== 数据主题相关 ==========
class DataThemeCreate(BaseCreateSchema):
    """创建数据主题请求"""
    theme_name: str = Field(..., min_length=1, max_length=100, description="主题名称")
    theme_description: Optional[str] = Field(None, description="主题描述")
    is_public: bool = Field(default=False, description="是否公共主题")
    sort_order: int = Field(default=0, description="排序序号")


class DataThemeUpdate(BaseUpdateSchema):
    """更新数据主题请求"""
    theme_name: Optional[str] = Field(None, min_length=1, max_length=100, description="主题名称")
    theme_description: Optional[str] = Field(None, description="主题描述")
    is_public: Optional[bool] = Field(None, description="是否公共主题")
    sort_order: Optional[int] = Field(None, description="排序序号")


class DataThemeResponse(BaseResponseSchema):
    """数据主题响应"""
    theme_name: str = Field(description="主题名称")
    theme_description: Optional[str] = Field(description="主题描述")
    is_public: bool = Field(description="是否公共主题")
    sort_order: int = Field(description="排序序号")
    table_count: Optional[int] = Field(default=0, description="包含的表数量")


class DataThemeListParams(BaseListParams):
    """数据主题列表查询参数"""
    is_public: Optional[bool] = Field(None, description="是否公共主题")


# ========== 表元数据相关 ==========
class TableCreate(BaseCreateSchema):
    """创建表元数据请求"""
    table_name_cn: str = Field(..., min_length=1, max_length=200, description="表中文名称")
    table_name_en: str = Field(..., min_length=1, max_length=200, description="表英文名称")
    data_source: Optional[str] = Field(None, max_length=100, description="数据源")
    update_method: UpdateMethodEnum = Field(default=UpdateMethodEnum.DAILY, description="更新方式")
    table_description: Optional[str] = Field(None, description="表描述")
    schema_name: Optional[str] = Field(None, max_length=100, description="模式名称")
    table_type: str = Field(default="table", max_length=50, description="表类型")
    row_count: Optional[int] = Field(None, ge=0, description="行数")
    size_mb: Optional[int] = Field(None, ge=0, description="大小(MB)")
    is_active: bool = Field(default=True, description="是否启用")
    is_visible: bool = Field(default=True, description="是否可见")
    theme_ids: Optional[List[int]] = Field(default=[], description="关联的主题ID列表")
    
    @validator('table_name_en')
    def validate_table_name_en(cls, v):
        """验证英文表名格式"""
        if not v.replace('_', '').isalnum():
            raise ValueError('表英文名称只能包含字母、数字和下划线')
        return v.lower()


class TableUpdate(BaseUpdateSchema):
    """更新表元数据请求"""
    table_name_cn: Optional[str] = Field(None, min_length=1, max_length=200, description="表中文名称")
    table_name_en: Optional[str] = Field(None, min_length=1, max_length=200, description="表英文名称")
    data_source: Optional[str] = Field(None, max_length=100, description="数据源")
    update_method: Optional[UpdateMethodEnum] = Field(None, description="更新方式")
    table_description: Optional[str] = Field(None, description="表描述")
    schema_name: Optional[str] = Field(None, max_length=100, description="模式名称")
    table_type: Optional[str] = Field(None, max_length=50, description="表类型")
    row_count: Optional[int] = Field(None, ge=0, description="行数")
    size_mb: Optional[int] = Field(None, ge=0, description="大小(MB)")
    is_active: Optional[bool] = Field(None, description="是否启用")
    is_visible: Optional[bool] = Field(None, description="是否可见")
    theme_ids: Optional[List[int]] = Field(None, description="关联的主题ID列表")


class TableResponse(BaseResponseSchema):
    """表元数据响应"""
    table_name_cn: str = Field(description="表中文名称")
    table_name_en: str = Field(description="表英文名称")
    data_source: Optional[str] = Field(description="数据源")
    update_method: UpdateMethodEnum = Field(description="更新方式")
    table_description: Optional[str] = Field(description="表描述")
    schema_name: Optional[str] = Field(description="模式名称")
    table_type: str = Field(description="表类型")
    row_count: Optional[int] = Field(description="行数")
    size_mb: Optional[int] = Field(description="大小(MB)")
    is_active: bool = Field(description="是否启用")
    is_visible: bool = Field(description="是否可见")
    field_count: Optional[int] = Field(default=0, description="字段数量")
    themes: Optional[List[DataThemeResponse]] = Field(default=[], description="关联的主题")


class TableListParams(BaseListParams):
    """表列表查询参数"""
    data_source: Optional[str] = Field(None, description="数据源")
    update_method: Optional[UpdateMethodEnum] = Field(None, description="更新方式")
    is_active: Optional[bool] = Field(None, description="是否启用")
    is_visible: Optional[bool] = Field(None, description="是否可见")
    theme_id: Optional[int] = Field(None, description="主题ID")


# ========== 字段元数据相关 ==========
class FieldCreate(BaseCreateSchema):
    """创建字段元数据请求"""
    table_id: int = Field(..., description="表ID")
    field_name_cn: str = Field(..., min_length=1, max_length=200, description="字段中文名称")
    field_name_en: str = Field(..., min_length=1, max_length=200, description="字段英文名称")
    field_type: FieldTypeEnum = Field(..., description="字段类型")
    business_type: Optional[BusinessTypeEnum] = Field(None, description="业务类型")
    max_length: Optional[int] = Field(None, ge=0, description="最大长度")
    precision: Optional[int] = Field(None, ge=0, description="精度")
    scale: Optional[int] = Field(None, ge=0, description="小数位数")
    is_nullable: bool = Field(default=True, description="是否可为空")
    is_primary_key: bool = Field(default=False, description="是否主键")
    is_foreign_key: bool = Field(default=False, description="是否外键")
    default_value: Optional[str] = Field(None, max_length=500, description="默认值")
    field_description: Optional[str] = Field(None, description="字段描述")
    business_rules: Optional[str] = Field(None, description="业务规则")
    data_format: Optional[str] = Field(None, max_length=100, description="数据格式")
    value_range: Optional[str] = Field(None, max_length=500, description="取值范围")
    sample_values: Optional[str] = Field(None, description="示例值")
    association_id: Optional[str] = Field(None, max_length=100, description="关联ID")
    foreign_table_id: Optional[int] = Field(None, description="外键关联表ID")
    foreign_field_id: Optional[int] = Field(None, description="外键关联字段ID")
    desensitization_type: DesensitizationTypeEnum = Field(default=DesensitizationTypeEnum.NONE, description="脱敏类型")
    is_active: bool = Field(default=True, description="是否启用")
    is_indexed: bool = Field(default=False, description="是否有索引")


class FieldUpdate(BaseUpdateSchema):
    """更新字段元数据请求"""
    field_name_cn: Optional[str] = Field(None, min_length=1, max_length=200, description="字段中文名称")
    field_name_en: Optional[str] = Field(None, min_length=1, max_length=200, description="字段英文名称")
    field_type: Optional[FieldTypeEnum] = Field(None, description="字段类型")
    business_type: Optional[BusinessTypeEnum] = Field(None, description="业务类型")
    max_length: Optional[int] = Field(None, ge=0, description="最大长度")
    precision: Optional[int] = Field(None, ge=0, description="精度")
    scale: Optional[int] = Field(None, ge=0, description="小数位数")
    is_nullable: Optional[bool] = Field(None, description="是否可为空")
    is_primary_key: Optional[bool] = Field(None, description="是否主键")
    is_foreign_key: Optional[bool] = Field(None, description="是否外键")
    default_value: Optional[str] = Field(None, max_length=500, description="默认值")
    field_description: Optional[str] = Field(None, description="字段描述")
    business_rules: Optional[str] = Field(None, description="业务规则")
    data_format: Optional[str] = Field(None, max_length=100, description="数据格式")
    value_range: Optional[str] = Field(None, max_length=500, description="取值范围")
    sample_values: Optional[str] = Field(None, description="示例值")
    association_id: Optional[str] = Field(None, max_length=100, description="关联ID")
    foreign_table_id: Optional[int] = Field(None, description="外键关联表ID")
    foreign_field_id: Optional[int] = Field(None, description="外键关联字段ID")
    desensitization_type: Optional[DesensitizationTypeEnum] = Field(None, description="脱敏类型")
    is_active: Optional[bool] = Field(None, description="是否启用")
    is_indexed: Optional[bool] = Field(None, description="是否有索引")


class FieldResponse(BaseResponseSchema):
    """字段元数据响应"""
    table_id: int = Field(description="表ID")
    field_name_cn: str = Field(description="字段中文名称")
    field_name_en: str = Field(description="字段英文名称")
    field_type: FieldTypeEnum = Field(description="字段类型")
    business_type: Optional[BusinessTypeEnum] = Field(description="业务类型")
    max_length: Optional[int] = Field(description="最大长度")
    precision: Optional[int] = Field(description="精度")
    scale: Optional[int] = Field(description="小数位数")
    is_nullable: bool = Field(description="是否可为空")
    is_primary_key: bool = Field(description="是否主键")
    is_foreign_key: bool = Field(description="是否外键")
    default_value: Optional[str] = Field(description="默认值")
    field_description: Optional[str] = Field(description="字段描述")
    business_rules: Optional[str] = Field(description="业务规则")
    data_format: Optional[str] = Field(description="数据格式")
    value_range: Optional[str] = Field(description="取值范围")
    sample_values: Optional[str] = Field(description="示例值")
    association_id: Optional[str] = Field(description="关联ID")
    foreign_table_id: Optional[int] = Field(description="外键关联表ID")
    foreign_field_id: Optional[int] = Field(description="外键关联字段ID")
    desensitization_type: DesensitizationTypeEnum = Field(description="脱敏类型")
    is_active: bool = Field(description="是否启用")
    is_indexed: bool = Field(description="是否有索引")
    distinct_count: Optional[int] = Field(description="唯一值数量")
    null_count: Optional[int] = Field(description="空值数量")
    
    # 关联信息
    table_name_cn: Optional[str] = Field(description="所属表中文名")
    table_name_en: Optional[str] = Field(description="所属表英文名")


class FieldListParams(BaseListParams):
    """字段列表查询参数"""
    table_id: Optional[int] = Field(None, description="表ID")
    field_type: Optional[FieldTypeEnum] = Field(None, description="字段类型")
    business_type: Optional[BusinessTypeEnum] = Field(None, description="业务类型")
    is_active: Optional[bool] = Field(None, description="是否启用")
    is_primary_key: Optional[bool] = Field(None, description="是否主键")
    is_foreign_key: Optional[bool] = Field(None, description="是否外键")


# ========== 术语表相关 ==========
class GlossaryCreate(BaseCreateSchema):
    """创建术语请求"""
    term_name: str = Field(..., min_length=1, max_length=200, description="术语名称")
    term_description: str = Field(..., min_length=1, description="术语描述")
    term_type: TermTypeEnum = Field(default=TermTypeEnum.USER, description="术语类型")
    category: Optional[str] = Field(None, max_length=100, description="术语分类")
    aliases: Optional[List[str]] = Field(default=[], description="别名列表")
    related_terms: Optional[List[str]] = Field(default=[], description="相关术语列表")
    examples: Optional[str] = Field(None, description="使用示例")
    data_sources: Optional[str] = Field(None, description="相关数据源")


class GlossaryUpdate(BaseUpdateSchema):
    """更新术语请求"""
    term_name: Optional[str] = Field(None, min_length=1, max_length=200, description="术语名称")
    term_description: Optional[str] = Field(None, min_length=1, description="术语描述")
    term_type: Optional[TermTypeEnum] = Field(None, description="术语类型")
    category: Optional[str] = Field(None, max_length=100, description="术语分类")
    aliases: Optional[List[str]] = Field(None, description="别名列表")
    related_terms: Optional[List[str]] = Field(None, description="相关术语列表")
    examples: Optional[str] = Field(None, description="使用示例")
    data_sources: Optional[str] = Field(None, description="相关数据源")


class GlossaryResponse(BaseResponseSchema):
    """术语响应"""
    term_name: str = Field(description="术语名称")
    term_description: str = Field(description="术语描述")
    term_type: TermTypeEnum = Field(description="术语类型")
    category: Optional[str] = Field(description="术语分类")
    aliases: List[str] = Field(default=[], description="别名列表")
    related_terms: List[str] = Field(default=[], description="相关术语列表")
    examples: Optional[str] = Field(description="使用示例")
    data_sources: Optional[str] = Field(description="相关数据源")
    usage_count: int = Field(default=0, description="使用次数")
    last_used_at: Optional[datetime] = Field(description="最后使用时间")
    user_id: Optional[int] = Field(description="创建用户ID")


class GlossaryListParams(BaseListParams):
    """术语列表查询参数"""
    term_type: Optional[TermTypeEnum] = Field(None, description="术语类型")
    category: Optional[str] = Field(None, description="术语分类")
    user_id: Optional[int] = Field(None, description="用户ID")


# ========== 表关联关系相关 ==========
class RelationCreate(BaseCreateSchema):
    """创建表关联关系请求"""
    source_table_id: int = Field(..., description="源表ID")
    target_table_id: int = Field(..., description="目标表ID")
    source_field_id: Optional[int] = Field(None, description="源字段ID")
    target_field_id: Optional[int] = Field(None, description="目标字段ID")
    relation_type: str = Field(..., description="关系类型")
    relation_name: Optional[str] = Field(None, max_length=200, description="关系名称")
    relation_description: Optional[str] = Field(None, description="关系描述")
    is_active: bool = Field(default=True, description="是否启用")


class RelationUpdate(BaseUpdateSchema):
    """更新表关联关系请求"""
    source_field_id: Optional[int] = Field(None, description="源字段ID")
    target_field_id: Optional[int] = Field(None, description="目标字段ID")
    relation_type: Optional[str] = Field(None, description="关系类型")
    relation_name: Optional[str] = Field(None, max_length=200, description="关系名称")
    relation_description: Optional[str] = Field(None, description="关系描述")
    is_active: Optional[bool] = Field(None, description="是否启用")


class RelationResponse(BaseResponseSchema):
    """表关联关系响应"""
    source_table_id: int = Field(description="源表ID")
    target_table_id: int = Field(description="目标表ID")
    source_field_id: Optional[int] = Field(description="源字段ID")
    target_field_id: Optional[int] = Field(description="目标字段ID")
    relation_type: str = Field(description="关系类型")
    relation_name: Optional[str] = Field(description="关系名称")
    relation_description: Optional[str] = Field(description="关系描述")
    is_active: bool = Field(description="是否启用")
    
    # 关联信息
    source_table_name: Optional[str] = Field(description="源表名称")
    target_table_name: Optional[str] = Field(description="目标表名称")
    source_field_name: Optional[str] = Field(description="源字段名称")
    target_field_name: Optional[str] = Field(description="目标字段名称")