"""
FraudHunter系统配置相关Pydantic schemas
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Any, Dict
from datetime import datetime


class SystemConfigBase(BaseModel):
    """系统配置基础模型"""
    config_category: str = Field(..., description="配置分类: sql_variable/system_param")
    config_key: str = Field(..., max_length=64, description="配置键")
    config_desc: str = Field(..., max_length=256, description="配置描述")
    config_type: str = Field(..., description="值类型: string/list/json_list")
    config_value: Dict[str, Any] = Field(..., description="配置值")
    sql_in_convert: bool = Field(False, description="列表是否转换为SQL IN格式")
    sort_order: int = Field(0, ge=0, description="排序顺序")

    @field_validator('config_category')
    @classmethod
    def validate_category(cls, v):
        if v not in ['sql_variable', 'system_param']:
            raise ValueError('config_category必须是sql_variable或system_param')
        return v

    @field_validator('config_type')
    @classmethod
    def validate_type(cls, v):
        if v not in ['string', 'list', 'json_list']:
            raise ValueError('config_type必须是string、list或json_list')
        return v

    @field_validator('config_value')
    @classmethod
    def validate_value(cls, v, info):
        if 'value' not in v:
            raise ValueError('config_value必须包含value字段')
        return v


class SystemConfigCreate(SystemConfigBase):
    """创建系统配置请求模型"""
    pass


class SystemConfigUpdate(SystemConfigBase):
    """更新系统配置请求模型"""
    pass


class SystemConfigResponse(SystemConfigBase):
    """系统配置响应模型"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SystemConfigListResponse(BaseModel):
    """系统配置列表响应模型"""
    total: int
    page: int
    page_size: int
    items: List[SystemConfigResponse]


class ExcelParseRequest(BaseModel):
    """Excel解析请求（用于预览）"""
    pass


class ExcelParseResponse(BaseModel):
    """Excel解析响应"""
    columns: List[str] = Field(..., description="列名列表")
    data: List[Dict[str, Any]] = Field(..., description="数据行列表")
    row_count: int = Field(..., description="数据行数")
