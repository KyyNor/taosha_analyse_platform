"""
批量创建指标相关Pydantic schemas
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
import json

from schemas.fraudhunter.indicator import IndicatorTaskCreate


class IndicatorBatchCreateItem(BaseModel):
    """批量创建中的单个指标"""
    indicator_name: str = Field(..., min_length=1, max_length=128, description="指标名称")
    description: Optional[str] = Field(None, description="指标描述")
    data_type: str = Field(..., description="数据类型：numeric/enum/text/boolean")
    enum_values: Optional[str] = Field(None, description="枚举值（JSON数组格式）")

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


class IndicatorTaskBatchCreate(BaseModel):
    """批量创建指标请求模型"""
    # 公共属性（所有指标共享）
    indicator_type: str = Field(..., description="指标类型：offline/realtime")
    object_type: str = Field(..., description="对象类型：cust_no/dep_acct_no/loan_acct_no")

    # 新建指标任务数据
    task_data: IndicatorTaskCreate = Field(..., description="指标任务数据")

    # 批量指标数据
    indicators: List[IndicatorBatchCreateItem] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="指标列表（1-50个）"
    )

    @field_validator('indicator_type')
    @classmethod
    def validate_indicator_type(cls, v):
        if v not in ['offline', 'realtime']:
            raise ValueError('indicator_type必须是offline或realtime')
        return v

    @field_validator('object_type')
    @classmethod
    def validate_object_type(cls, v):
        if v not in ['cust_no', 'dep_acct_no', 'loan_acct_no']:
            raise ValueError('object_type必须是cust_no、dep_acct_no或loan_acct_no')
        return v

    @field_validator('indicators')
    @classmethod
    def validate_indicators(cls, v):
        if not v or len(v) == 0:
            raise ValueError('指标列表不能为空')
        if len(v) > 50:
            raise ValueError('单次最多创建50个指标')
        return v


class IndicatorBatchCreateResult(BaseModel):
    """批量创建中单个指标的结果"""
    index: int = Field(..., description="指标在列表中的索引")
    success: bool = Field(..., description="是否创建成功")
    indicator: Optional[dict] = Field(None, description="创建成功的指标数据（包含ID）")
    error: Optional[str] = Field(None, description="错误信息")


class IndicatorBatchCreateResponse(BaseModel):
    """批量创建响应模型"""
    task_id: int = Field(..., description="指标任务ID（新建）")
    task_code: str = Field(..., description="指标任务编码")
    task_name: str = Field(..., description="指标任务名称")
    total: int = Field(..., description="总共尝试创建的指标数")
    success_count: int = Field(..., description="成功创建的指标数")
    failed_count: int = Field(..., description="失败的指标数")
    results: List[IndicatorBatchCreateResult] = Field(..., description="每个指标的创建结果")


class CreateTaskWithIndicatorsRequest(BaseModel):
    """创建任务并关联指标的请求模型"""
    task_data: IndicatorTaskCreate = Field(..., description="指标任务数据")
    indicator_ids: List[int] = Field(..., min_length=1, description="指标ID列表")

    @field_validator('indicator_ids')
    @classmethod
    def validate_indicator_ids(cls, v):
        if not v or len(v) == 0:
            raise ValueError('指标ID列表不能为空')
        return v


class CreateTaskWithIndicatorsResponse(BaseModel):
    """创建任务并关联指标的响应模型"""
    task_id: int = Field(..., description="任务ID")
    task_code: str = Field(..., description="任务编码")
    task_name: str = Field(..., description="任务名称")
    indicator_count: int = Field(..., description="关联的指标数量")
    indicator_ids: List[int] = Field(..., description="关联的指标ID列表")