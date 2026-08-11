"""
告警管控记录相关的Schema定义
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime, date


class AlertControlFilters(BaseModel):
    """告警管控记录筛选条件"""
    
    # 日期范围
    start_date: Optional[str] = Field(None, description="开始日期 (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="结束日期 (YYYY-MM-DD)")
    
    # 账号筛选
    account_id: Optional[str] = Field(None, description="账号ID")

    # 机构筛选
    branch_no: Optional[str] = Field(None, description="机构号（精确匹配）")
    
    # 模型筛选
    model_ids: Optional[List[int]] = Field(None, description="模型ID列表（多选）")
    model_name: Optional[str] = Field(None, description="模型名称")
    
    # 状态筛选
    alert_status: Optional[str] = Field(None, description="告警状态：not_configured/sent/duplicate")
    control_status: Optional[str] = Field(None, description="管控状态：not_configured/executed/duplicate")
    
    # 搜索关键词
    search: Optional[str] = Field(None, description="搜索关键词")

    # 隐藏无效记录（告警和管控均为重复或未配置）
    hide_inactive: Optional[bool] = Field(None, description="隐藏无效记录")


class PaginationParams(BaseModel):
    """分页参数"""
    
    page: int = Field(1, ge=1, description="页码，从1开始")
    page_size: int = Field(20, ge=1, le=1000, description="每页大小，最大1000")


class AlertControlRecordResponse(BaseModel):
    """告警管控记录响应"""

    id: int
    hit_record_id: int
    account_id: str
    branch_no: Optional[str] = None
    record_date: date
    hit_model_ids: List[int]
    hit_model_names: List[str]

    # 告警信息
    alert_status: str
    alert_message: Optional[str] = None
    alert_person: Optional[str] = None
    alert_time: Optional[datetime] = None

    # 管控信息
    control_status: str
    control_time: Optional[datetime] = None
    control_serial_number: Optional[str] = None

    # 审计信息
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AlertControlListResponse(BaseModel):
    """告警管控记录列表响应"""
    
    records: List[AlertControlRecordResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class HitRecordResponse(BaseModel):
    """命中记录响应"""

    id: int
    account_id: str
    branch_no: Optional[str] = None
    hit_time: datetime
    hit_model_ids: List[int]
    hit_model_names: List[str]
    indicator_data: dict
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class AlertControlRecordDetailResponse(BaseModel):
    """告警管控记录详情响应"""

    # 基本信息
    record: AlertControlRecordResponse

    # 关联的命中记录
    hit_record: HitRecordResponse


class TrendRequest(BaseModel):
    """历史趋势请求参数"""

    start_date: str = Field(..., description="开始日期 (YYYY-MM-DD)")
    end_date: str = Field(..., description="结束日期 (YYYY-MM-DD)")
    granularity: Literal["day", "week", "month"] = "day"
    model_ids: Optional[List[int]] = Field(None, description="模型ID列表（多选）")


class TrendPoint(BaseModel):
    """历史趋势数据点"""

    date_point: str = Field(..., description="时间刻度（格式取决于粒度：YYYY-MM-DD / YYYY-Wxx / YYYY-MM）")
    model_id: int
    model_name: str
    distinct_account_count: int

    class Config:
        from_attributes = True


class TrendResponse(BaseModel):
    """历史趋势响应"""

    series: List[TrendPoint] = Field(default_factory=list)
    total_points: int = 0
    meta: dict = Field(default_factory=dict)


class AlertControlListRequest(BaseModel):
    """告警管控记录列表请求（POST）"""

    # 分页
    page: int = Field(1, ge=1, description="页码，从1开始")
    page_size: int = Field(20, ge=1, le=1000, description="每页大小，最大1000")

    # 筛选
    start_date: Optional[str] = Field(None, description="开始日期 (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="结束日期 (YYYY-MM-DD)")
    account_id: Optional[str] = Field(None, description="账号ID")
    branch_no: Optional[str] = Field(None, description="机构号（精确匹配）")
    model_ids: Optional[List[int]] = Field(None, description="模型ID列表（多选）")
    model_name: Optional[str] = Field(None, description="模型名称（模糊匹配）")
    alert_status: Optional[str] = Field(None, description="告警状态：not_configured/sent/duplicate")
    control_status: Optional[str] = Field(None, description="管控状态：not_configured/executed/duplicate")
    search: Optional[str] = Field(None, description="搜索关键词")
    hide_inactive: Optional[bool] = Field(None, description="隐藏无效记录")


class AlertControlExportRequest(BaseModel):
    """告警管控记录导出请求（POST）"""

    start_date: Optional[str] = Field(None, description="开始日期 (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="结束日期 (YYYY-MM-DD)")
    account_id: Optional[str] = Field(None, description="账号ID")
    branch_no: Optional[str] = Field(None, description="机构号（精确匹配）")
    model_ids: Optional[List[int]] = Field(None, description="模型ID列表（多选）")
    model_name: Optional[str] = Field(None, description="模型名称（模糊匹配）")
    alert_status: Optional[str] = Field(None, description="告警状态：not_configured/sent/duplicate")
    control_status: Optional[str] = Field(None, description="管控状态：not_configured/executed/duplicate")
    search: Optional[str] = Field(None, description="搜索关键词")
    hide_inactive: Optional[bool] = Field(None, description="隐藏无效记录")
    format: Literal["csv", "excel"] = Field("excel", description="导出格式")
