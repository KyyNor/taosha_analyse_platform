"""
FraudHunter指标相关Pydantic schemas
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime, date
import json


# ==================== 指标组相关 ====================

class IndicatorGroupBase(BaseModel):
    """指标组基础模型"""
    group_code: str = Field(..., min_length=1, max_length=64, description="指标组编码")
    group_name: str = Field(..., min_length=1, max_length=128, description="指标组名称")
    description: Optional[str] = Field(None, description="描述")
    logic_type: str = Field("sql", description="逻辑类型：sql/pyspark")
    logic_content: str = Field(..., min_length=1, description="SQL内容或代码")
    source_tables: Optional[str] = Field(None, description="依赖的源表列表，逗号分隔")
    output_table: Optional[str] = Field("anti_fraud.indicator_result_row", description="输出表名")
    output_mode: str = Field("row", description="输出模式：row（行存）")


class IndicatorGroupCreate(IndicatorGroupBase):
    """创建指标组请求模型"""
    pass


class IndicatorGroupUpdate(BaseModel):
    """更新指标组请求模型"""
    group_name: Optional[str] = Field(None, min_length=1, max_length=128)
    description: Optional[str] = None
    logic_content: Optional[str] = Field(None, min_length=1)
    source_tables: Optional[str] = None
    output_table: Optional[str] = None


class IndicatorGroupResponse(IndicatorGroupBase):
    """指标组响应模型"""
    id: int
    current_version: int
    latest_version: int
    status: str
    created_by: Optional[str]
    created_at: datetime
    updated_by: Optional[str]
    updated_at: datetime

    class Config:
        from_attributes = True


class IndicatorGroupListResponse(BaseModel):
    """指标组列表响应模型"""
    total: int
    page: int
    page_size: int
    items: List[IndicatorGroupResponse]


# ==================== 指标定义相关 ====================

class IndicatorBase(BaseModel):
    """指标基础模型"""
    indicator_code: str = Field(..., min_length=1, max_length=64, description="指标编码")
    indicator_name: str = Field(..., min_length=1, max_length=128, description="指标名称")
    indicator_type: str = Field(..., description="指标类型：offline/realtime")
    description: Optional[str] = Field(None, description="指标描述")
    data_type: str = Field(..., description="数据类型：numeric/enum/text/boolean")
    enum_values: Optional[str] = Field(None, description="枚举值（JSON数组格式）")
    indicator_group_id: int = Field(..., description="指标组ID")

    @field_validator('indicator_type')
    @classmethod
    def validate_indicator_type(cls, v):
        if v not in ['offline', 'realtime']:
            raise ValueError('indicator_type必须是offline或realtime')
        return v

    @field_validator('data_type')
    @classmethod
    def validate_data_type(cls, v):
        if v not in ['numeric', 'enum', 'text', 'boolean']:
            raise ValueError('data_type必须是numeric、enum、text或boolean')
        return v

    @field_validator('enum_values')
    @classmethod
    def validate_enum_values(cls, v, info):
        if v is not None and info.data.get('data_type') == 'enum':
            try:
                values = json.loads(v)
                if not isinstance(values, list):
                    raise ValueError('enum_values必须是JSON数组格式')
            except json.JSONDecodeError:
                raise ValueError('enum_values必须是有效的JSON数组')
        return v


class IndicatorCreate(IndicatorBase):
    """创建指标请求模型"""
    pass


class IndicatorUpdate(BaseModel):
    """更新指标请求模型"""
    indicator_name: Optional[str] = Field(None, min_length=1, max_length=128)
    description: Optional[str] = None
    data_type: Optional[str] = None
    enum_values: Optional[str] = None


class IndicatorResponse(IndicatorBase):
    """指标响应模型"""
    id: int
    current_version: int
    latest_version: int
    status: str
    created_by: Optional[str]
    created_at: datetime
    updated_by: Optional[str]
    updated_at: datetime

    class Config:
        from_attributes = True


class IndicatorListResponse(BaseModel):
    """指标列表响应模型"""
    total: int
    page: int
    page_size: int
    items: List[IndicatorResponse]


# ==================== 试运行相关 ====================

class DryRunRequest(BaseModel):
    """试运行请求模型"""
    etl_date: str = Field(..., description="ETL日期，格式：2025-10-20")
    group_version: Optional[int] = Field(None, description="指标组版本号")
    sample_size: Optional[int] = Field(100, ge=1, le=10000, description="样本大小")

    @field_validator('etl_date')
    @classmethod
    def validate_etl_date(cls, v):
        try:
            datetime.strptime(v, '%Y-%m-%d')
        except ValueError:
            raise ValueError('etl_date格式必须是YYYY-MM-DD')
        return v


class DryRunResponse(BaseModel):
    """试运行响应模型"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
    message: str = Field(..., description="提示信息")


# ==================== 发布相关 ====================

class PublishRequest(BaseModel):
    """发布请求模型"""
    version: int = Field(..., ge=1, description="要发布的版本号")
    change_description: Optional[str] = Field(None, description="变更说明")
