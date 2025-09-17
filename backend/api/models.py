"""
API数据模型定义
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class QueryRequest(BaseModel):
    """查询请求模型"""
    query: str = Field(..., description="自然语言查询", min_length=1)

class QueryResponse(BaseModel):
    """查询响应模型"""
    success: bool = Field(..., description="查询是否成功")
    user_input: str = Field(..., description="用户输入")
    is_clear: bool = Field(..., description="输入是否清晰")
    sql_query: str = Field("", description="生成的SQL查询")
    clear_check_details: Optional[Dict[str, Any]] = Field(None, description="输入清晰度验证结果")
    data: Optional[List[Dict[str, Any]]] = Field(None, description="查询结果数据")
    row_count: Optional[int] = Field(None, description="结果行数")
    error: Optional[str] = Field(None, description="错误信息")
    retry_count: int = Field(0, description="重试次数")
    execution_time: float = Field(..., description="执行时间(秒)")
    logs: List[Dict[str, Any]] = Field([], description="执行日志")

class TableInfo(BaseModel):
    """表信息模型"""
    table_name: str = Field(..., description="表名")
    comment: str = Field("", description="表注释")
    row_count: int = Field(0, description="行数")
    columns: List[Dict[str, Any]] = Field([], description="列信息")

class DatabaseStatus(BaseModel):
    """数据库状态模型"""
    database_type: str = Field(..., description="数据库类型")
    tables: List[TableInfo] = Field([], description="表列表")
    total_tables: int = Field(0, description="表总数")

class SystemStatus(BaseModel):
    """系统状态模型"""
    app_name: str = Field(..., description="应用名称")
    version: str = Field(..., description="版本号")
    status: str = Field(..., description="运行状态")
    database: DatabaseStatus = Field(..., description="数据库状态")
    metadata_version: str = Field("", description="元数据版本")
    glossary_version: str = Field("", description="术语表版本")
    uptime: str = Field("", description="运行时间")

class ErrorResponse(BaseModel):
    """错误响应模型"""
    error: str = Field(..., description="错误信息")
    detail: Optional[str] = Field(None, description="错误详情")
    timestamp: datetime = Field(default_factory=datetime.now, description="错误时间")