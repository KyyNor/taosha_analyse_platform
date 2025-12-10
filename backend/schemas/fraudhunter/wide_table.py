"""
FraudHunter宽表版本管理相关Pydantic schemas
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict
from datetime import datetime, date


class IndicatorRunProgressCallback(BaseModel):
    """指标运行进度回调请求模型（精简版）"""

    indicator_task_id: int = Field(..., description="指标任务ID", gt=0)
    indicator_version: int = Field(..., description="指标版本号", gt=0)
    etl_date: str = Field(..., description="ETL日期，格式: YYYY-MM-DD")

    @field_validator('etl_date')
    @classmethod
    def validate_etl_date(cls, v: str) -> str:
        """验证ETL日期格式"""
        try:
            datetime.strptime(v, '%Y-%m-%d')
        except ValueError:
            raise ValueError('etl_date格式必须是YYYY-MM-DD')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "indicator_task_id": 123,
                "indicator_version": 2,
                "etl_date": "2025-12-06"
            }
        }


class IndicatorRunProgressResponse(BaseModel):
    """指标运行进度回调响应模型"""

    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="提示信息")
    progress_id: Optional[int] = Field(None, description="进度记录ID")
    version_sync_triggered: bool = Field(False, description="是否触发了版本同步检查")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "运行进度已更新",
                "progress_id": 456,
                "version_sync_triggered": False
            }
        }


class WideTableVersionInfo(BaseModel):
    """宽表版本信息响应模型"""

    id: int = Field(..., description="版本ID")
    wide_table_name: str = Field(..., description="宽表名称")
    version_hash: str = Field(..., description="版本号(SHA256 hash)")
    indicator_metadata: Dict = Field(..., description="参与指标的元数据")
    status: str = Field(..., description="状态: current/target/history/skipped")
    target_at: Optional[datetime] = Field(None, description="成为target的时间")
    current_at: Optional[datetime] = Field(None, description="成为current的时间")
    history_at: Optional[datetime] = Field(None, description="成为history的时间")
    skipped_at: Optional[datetime] = Field(None, description="成为skipped的时间")
    created_by: Optional[str] = Field(None, description="创建人")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class IndicatorProgressInfo(BaseModel):
    """指标执行进度信息"""

    indicator_id: int = Field(..., description="指标ID")
    indicator_code: str = Field(..., description="指标编码")
    indicator_name: str = Field(..., description="指标名称")
    indicator_type: str = Field(..., description="指标类型")
    indicator_version: int = Field(..., description="指标版本号")
    indicator_task_id: Optional[int] = Field(None, description="指标任务ID")


class WideTableVersionDetailInfo(BaseModel):
    """宽表版本详情响应模型（含指标清单和执行进度）"""

    id: int = Field(..., description="版本ID")
    wide_table_name: str = Field(..., description="宽表名称")
    version_hash: str = Field(..., description="版本号(SHA256 hash)")
    indicator_metadata: Dict = Field(..., description="参与指标的元数据")
    status: str = Field(..., description="状态: current/target/history/skipped")
    target_at: Optional[datetime] = Field(None, description="成为target的时间")
    current_at: Optional[datetime] = Field(None, description="成为current的时间")
    history_at: Optional[datetime] = Field(None, description="成为history的时间")
    skipped_at: Optional[datetime] = Field(None, description="成为skipped的时间")
    created_by: Optional[str] = Field(None, description="创建人")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    # 扩展字段
    indicators: list[IndicatorProgressInfo] = Field(
        default_factory=list,
        description="包含的指标清单"
    )
    snapshot_count: int = Field(default=0, description="快照数量")
    completed_dates: list[str] = Field(
        default_factory=list,
        description="已完成执行的ETL日期列表"
    )

    class Config:
        from_attributes = True


class WideTableVersionProgressInfo(BaseModel):
    """宽表版本执行进度信息"""

    version_hash: str = Field(..., description="版本号")
    wide_table_name: str = Field(..., description="宽表名称")
    total_indicators: int = Field(..., description="指标总数")
    completed_dates: list[str] = Field(
        default_factory=list,
        description="已完成执行的ETL日期列表"
    )
    recent_progress: list[Dict] = Field(
        default_factory=list,
        description="最近的执行进度记录"
    )

    class Config:
        from_attributes = True


class WideTableVersionListResponse(BaseModel):
    """宽表版本列表响应模型"""

    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页数量")
    items: list[WideTableVersionInfo] = Field(default_factory=list, description="版本列表")

    class Config:
        from_attributes = True


class WideTableSnapshotInfo(BaseModel):
    """宽表快照信息响应模型"""

    id: int = Field(..., description="快照ID")
    wide_table_name: str = Field(..., description="宽表名称")
    etl_date: date = Field(..., description="ETL日期")
    version_hash: Optional[str] = Field(None, description="版本号(实时指标为NULL)")
    parquet_file_path: str = Field(..., description="Parquet文件路径")
    file_size_bytes: Optional[int] = Field(None, description="文件大小(字节)")
    row_count: Optional[int] = Field(None, description="行数")
    column_count: Optional[int] = Field(None, description="列数")
    status: str = Field(..., description="状态: generating/ready/failed")
    generation_time: Optional[datetime] = Field(None, description="生成时间")
    error_message: Optional[str] = Field(None, description="错误信息")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True
