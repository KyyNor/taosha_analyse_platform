"""
FraudHunter指标相关Pydantic schemas
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime, date
import json


# ==================== 指标任务相关 ====================

class IndicatorTaskBase(BaseModel):
    """指标任务基础模型"""
    task_code: Optional[str] = Field(None, max_length=64, description="指标任务编码（留空自动生成）")
    task_name: str = Field(..., min_length=1, max_length=128, description="指标任务名称")
    description: Optional[str] = Field(None, description="描述")
    logic_type: str = Field("sql", description="逻辑类型：sql/pyspark")
    logic_content: str = Field(..., min_length=1, description="SQL内容或代码")
    realtime_logic_content: str = Field(..., description="实时指标SQL")
    source_tables: Optional[str] = Field(None, description="依赖的源表列表，逗号分隔")
    object_type: str = Field(..., description="对象类型：cust_no/dep_acct_no/loan_acct_no")

    @field_validator('object_type')
    @classmethod
    def validate_object_type(cls, v):
        if v not in ['cust_no', 'dep_acct_no', 'loan_acct_no']:
            raise ValueError('object_type必须是cust_no、dep_acct_no或loan_acct_no')
        return v


class IndicatorTaskCreate(IndicatorTaskBase):
    """创建指标任务请求模型"""
    pass


class IndicatorTaskUpdate(BaseModel):
    """更新指标任务请求模型"""
    task_name: Optional[str] = Field(None, min_length=1, max_length=128)
    description: Optional[str] = None
    logic_content: Optional[str] = Field(None, min_length=1)
    realtime_logic_content: Optional[str] = None
    source_tables: Optional[str] = None
    object_type: Optional[str] = None


class IndicatorTaskResponse(IndicatorTaskBase):
    """指标任务响应模型"""
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


class IndicatorTaskListResponse(BaseModel):
    """指标任务列表响应模型"""
    total: int
    page: int
    page_size: int
    items: List[IndicatorTaskResponse]


# ==================== 指标定义相关 ====================

class IndicatorBase(BaseModel):
    """指标基础模型"""
    indicator_code: Optional[str] = Field(None, max_length=64, description="指标编码（留空自动生成）")
    indicator_name: str = Field(..., min_length=1, max_length=128, description="指标名称")
    indicator_type: str = Field(..., description="指标类型：offline/realtime")
    object_type: str = Field(..., description="对象类型：cust_no/dep_acct_no/loan_acct_no")
    description: Optional[str] = Field(None, description="指标描述")
    data_type: str = Field(..., description="数据类型：numeric/text/date")
    enum_values: Optional[str] = Field(None, description="枚举值（保留字段，暂不使用）")
    indicator_task_id: Optional[int] = Field(None, description="指标任务ID（留空表示未关联任务）")

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

    @field_validator('data_type')
    @classmethod
    def validate_data_type(cls, v):
        if v not in ['numeric', 'text', 'date']:
            raise ValueError('data_type必须是numeric、text或date')
        return v


class IndicatorCreate(IndicatorBase):
    """创建指标请求模型"""
    pass


class IndicatorUpdate(BaseModel):
    """更新指标请求模型"""
    indicator_name: Optional[str] = Field(None, min_length=1, max_length=128)
    description: Optional[str] = None
    object_type: Optional[str] = None
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
    task_version: Optional[int] = Field(None, description="指标任务版本号")
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


# ==================== DolphinScheduler 相关 ====================

class PublishToDSRequest(BaseModel):
    """上线到 DolphinScheduler 请求模型"""
    schedule_cron: Optional[str] = Field(None, description="定时调度表达式（cron），不填则使用默认配置")


class PublishToDSResponse(BaseModel):
    """上线到 DolphinScheduler 响应模型"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="提示信息")
    workflow_name: Optional[str] = Field(None, description="工作流名称")
    workflow_code: Optional[str] = Field(None, description="工作流编码")
    ds_task_name: Optional[str] = Field(None, description="DS任务名称")
    ds_task_code: Optional[str] = Field(None, description="DS任务编号")
    online_success: Optional[bool] = Field(None, description="调度是否上线成功")


class RerunRequest(BaseModel):
    """补数请求模型"""
    start_date: str = Field(..., description="开始日期，格式：YYYY-MM-DD")
    end_date: Optional[str] = Field(None, description="结束日期，格式：YYYY-MM-DD，默认为今天")

    @field_validator('start_date')
    @classmethod
    def validate_start_date(cls, v):
        try:
            datetime.strptime(v, '%Y-%m-%d')
        except ValueError:
            raise ValueError('start_date格式必须是YYYY-MM-DD')
        return v

    @field_validator('end_date')
    @classmethod
    def validate_end_date(cls, v):
        if v is not None:
            try:
                datetime.strptime(v, '%Y-%m-%d')
            except ValueError:
                raise ValueError('end_date格式必须是YYYY-MM-DD')
        return v


class RerunResponse(BaseModel):
    """补数响应模型"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="提示信息")
    workflow_code: Optional[str] = Field(None, description="工作流编码")
    start_date: str = Field(..., description="开始日期")
    end_date: Optional[str] = Field(None, description="结束日期")
