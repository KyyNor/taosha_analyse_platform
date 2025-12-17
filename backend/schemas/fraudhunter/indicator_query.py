"""
指标数据查询相关的Pydantic模型
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime, date


class IndicatorQueryCondition(BaseModel):
    """查询条件"""
    field: str = Field(..., description="字段名")
    operator: Literal["=", ">", "<", ">=", "<=", "like"] = Field(..., description="运算符")
    value: Any = Field(..., description="值")
    field_name: Optional[str] = Field(None, description="字段显示名称")


class WideTableFile(BaseModel):
    """宽表文件信息"""
    id: int = Field(..., description="快照ID")
    wide_table_name: str = Field(..., description="宽表名称")
    etl_date: date = Field(..., description="ETL日期")
    version_hash: Optional[str] = Field(None, description="版本哈希")
    file_path: str = Field(..., description="文件路径")
    status: str = Field(..., description="状态")
    generation_time: datetime = Field(..., description="生成时间")
    row_count: Optional[int] = Field(None, description="行数")
    column_count: Optional[int] = Field(None, description="列数")
    file_size_bytes: Optional[int] = Field(None, description="文件大小(字节)")
    is_realtime: bool = Field(False, description="是否实时表")


class IndicatorInfo(BaseModel):
    """指标信息"""
    id: int = Field(..., description="指标ID")
    indicator_code: str = Field(..., description="指标编码")
    indicator_name: str = Field(..., description="指标名称")
    indicator_type: str = Field(..., description="指标类型")
    data_type: str = Field(..., description="数据类型")
    object_type: str = Field(..., description="对象类型")


class IndicatorQueryRequest(BaseModel):
    """指标数据查询请求"""
    snapshot_id: int = Field(..., description="快照ID")
    target_id: Optional[str] = Field(None, description="目标ID精确查询")
    conditions: List[IndicatorQueryCondition] = Field(default_factory=list, description="查询条件列表，最多10个")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(100, ge=1, le=100, description="每页大小，最大100")

    class Config:
        json_schema_extra = {
            "example": {
                "snapshot_id": 1,
                "target_id": "CUST001",
                "conditions": [
                    {
                        "field": "age",
                        "operator": ">=",
                        "value": 18,
                        "field_name": "年龄"
                    },
                    {
                        "field": "customer_name",
                        "operator": "like",
                        "value": "张",
                        "field_name": "客户姓名"
                    }
                ],
                "page": 1,
                "page_size": 100
            }
        }


class IndicatorQueryResponse(BaseModel):
    """指标数据查询响应"""
    items: List[Dict[str, Any]] = Field(..., description="查询结果列表")
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页大小")