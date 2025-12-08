"""
FraudHunter预警管控模型管理相关Pydantic schemas
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
from .rule import RuleConfig


# ==================== 预警管控模型相关 ====================

class RiskControlModelBase(BaseModel):
    """预警管控模型基础模型"""
    model_code: Optional[str] = Field(None, max_length=64, description="模型编码（可选，不提供则自动生成）")
    model_name: str = Field(..., min_length=1, max_length=128, description="模型名称")
    description: Optional[str] = Field(None, description="模型描述")

    # 规则配置
    rule_config: RuleConfig = Field(..., description="规则配置JSON")

    # 告警配置
    is_send_alert_message: bool = Field(False, description="是否发送告警消息")
    alert_message_target: Optional[str] = Field(None, max_length=256, description="告警消息目标")
    is_acct_control: bool = Field(False, description="是否账户控制")

    @field_validator('object_type')
    @classmethod
    def validate_object_type(cls, v):
        if v not in ['cust_no', 'dep_acct_no', 'loan_acct_no']:
            raise ValueError('object_type必须是cust_no、dep_acct_no或loan_acct_no')
        return v


class RiskControlModelCreate(RiskControlModelBase):
    """创建预警管控模型请求模型"""
    pass


class RiskControlModelUpdate(BaseModel):
    """更新预警管控模型请求模型"""
    model_name: Optional[str] = Field(None, min_length=1, max_length=128, description="模型名称")
    description: Optional[str] = Field(None, description="模型描述")
    object_type: Optional[str] = Field(None, description="对象类型")
    rule_config: Optional[RuleConfig] = Field(None, description="规则配置")
    is_send_alert_message: Optional[bool] = Field(None, description="是否发送告警消息")
    alert_message_target: Optional[str] = Field(None, max_length=256, description="告警消息目标")
    is_acct_control: Optional[bool] = Field(None, description="是否账户控制")

    @field_validator('object_type')
    @classmethod
    def validate_object_type(cls, v):
        if v is not None and v not in ['cust_no', 'dep_acct_no', 'loan_acct_no']:
            raise ValueError('object_type必须是cust_no、dep_acct_no或loan_acct_no')
        return v


class RiskControlModelResponse(RiskControlModelBase):
    """预警管控模型响应模型"""
    id: int

    # 生成的SQL
    offline_model_sql: Optional[str] = None
    realtime_model_sql: Optional[str] = None

    # 关联指标
    indicator_codes: Optional[str] = None

    # 版本管理
    current_version: int
    latest_version: int

    # 状态
    status: str

    # 审计
    created_by: Optional[str] = None
    created_at: datetime
    updated_by: Optional[str] = None
    updated_at: datetime

    class Config:
        from_attributes = True


class RiskControlModelListResponse(BaseModel):
    """预警管控模型列表响应模型"""
    total: int
    page: int
    page_size: int
    items: List[RiskControlModelResponse]


# ==================== 发布相关 ====================

class RiskControlModelPublishRequest(BaseModel):
    """预警管控模型发布请求模型"""
    version: int = Field(..., ge=1, description="要发布的版本号")
    change_description: Optional[str] = Field(None, description="变更说明")


# ==================== 历史回测相关 ====================

class ModelBacktestRequest(BaseModel):
    """模型历史回测请求模型"""
    start_date: str = Field(..., description="开始日期 (YYYY-MM-DD)")
    end_date: str = Field(..., description="结束日期 (YYYY-MM-DD)")

    @field_validator('start_date', 'end_date')
    @classmethod
    def validate_date_format(cls, v):
        """验证日期格式"""
        try:
            datetime.strptime(v, '%Y-%m-%d')
        except ValueError:
            raise ValueError('日期格式必须是 YYYY-MM-DD')
        return v


class ModelBacktestResponse(BaseModel):
    """模型历史回测响应模型"""
    success: bool = Field(..., description="提交是否成功")
    message: str = Field(..., description="提示消息")
    execution_id: Optional[str] = Field(None, description="任务执行ID")


class ModelBacktestDayResult(BaseModel):
    """模型历史回测单日结果"""
    date: str = Field(..., description="日期")
    status: str = Field(..., description="状态: pending/success/skipped/failed")
    message: str = Field(..., description="消息")
    rows_matched: int = Field(default=0, description="命中记录数")


class ModelBacktestResult(BaseModel):
    """模型历史回测完整结果"""
    total_days: int = Field(..., description="总天数")
    success_days: int = Field(..., description="成功天数")
    skipped_days: int = Field(..., description="跳过天数")
    failed_days: int = Field(..., description="失败天数")
    total_rows_matched: int = Field(default=0, description="总命中记录数")
    daily_results: List[ModelBacktestDayResult] = Field(default_factory=list, description="每日结果")
    warnings: List[str] = Field(default_factory=list, description="警告信息")


# ==================== 模型上线相关 ====================

class ModelOnlineRequest(BaseModel):
    """模型上线请求模型（预留）"""
    schedule_cron: Optional[str] = Field(None, description="调度CRON表达式")
    description: Optional[str] = Field(None, description="上线说明")


class ModelOnlineResponse(BaseModel):
    """模型上线响应模型（预留）"""
    success: bool = Field(..., description="上线是否成功")
    message: str = Field(..., description="提示消息")
    workflow_code: Optional[str] = Field(None, description="DolphinScheduler工作流编码")
