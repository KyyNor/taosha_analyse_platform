"""
查询历史相关的Pydantic模型
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class QueryStatusEnum(str, Enum):
    """查询状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class QueryHistoryBase(BaseModel):
    """查询历史基础模型"""
    user_question: str = Field(..., description="用户问题")
    theme_id: Optional[int] = Field(None, description="数据主题ID")
    table_ids: Optional[List[int]] = Field(None, description="相关表ID列表")


class QueryHistoryCreate(QueryHistoryBase):
    """创建查询历史请求模型"""
    task_id: str = Field(..., description="任务ID")
    user_id: int = Field(..., description="用户ID")
    generated_sql: Optional[str] = Field(None, description="生成的SQL")
    status: QueryStatusEnum = Field(QueryStatusEnum.PENDING, description="查询状态")


class QueryHistoryUpdate(BaseModel):
    """更新查询历史请求模型"""
    status: Optional[QueryStatusEnum] = Field(None, description="查询状态")
    generated_sql: Optional[str] = Field(None, description="生成的SQL")
    final_sql: Optional[str] = Field(None, description="最终执行的SQL")
    result_count: Optional[int] = Field(None, description="结果行数")
    execution_time_ms: Optional[int] = Field(None, description="执行时间(毫秒)")
    error_message: Optional[str] = Field(None, description="错误信息")
    llm_tokens_used: Optional[int] = Field(None, description="LLM使用的token数")


class QueryHistoryResponse(QueryHistoryBase):
    """查询历史响应模型"""
    id: int = Field(..., description="历史记录ID")
    task_id: str = Field(..., description="任务ID")
    user_id: int = Field(..., description="用户ID")
    status: QueryStatusEnum = Field(..., description="查询状态")
    generated_sql: Optional[str] = Field(None, description="生成的SQL")
    final_sql: Optional[str] = Field(None, description="最终执行的SQL")
    result_count: Optional[int] = Field(None, description="结果行数")
    execution_time_ms: Optional[int] = Field(None, description="执行时间(毫秒)")
    error_message: Optional[str] = Field(None, description="错误信息")
    llm_tokens_used: Optional[int] = Field(None, description="LLM使用的token数")
    is_favorite: bool = Field(False, description="是否收藏")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    
    # 关联信息
    theme_name: Optional[str] = Field(None, description="数据主题名称")
    table_names: Optional[List[str]] = Field(None, description="相关表名称列表")

    class Config:
        from_attributes = True


class QueryHistoryFilter(BaseModel):
    """查询历史筛选条件"""
    user_id: int = Field(..., description="用户ID")
    status: Optional[QueryStatusEnum] = Field(None, description="查询状态")
    theme_id: Optional[int] = Field(None, description="数据主题ID")
    start_date: Optional[datetime] = Field(None, description="开始时间")
    end_date: Optional[datetime] = Field(None, description="结束时间")
    keyword: Optional[str] = Field(None, description="关键词搜索")


class QueryHistoryStatistics(BaseModel):
    """查询历史统计信息"""
    total_queries: int = Field(..., description="总查询数")
    successful_queries: int = Field(..., description="成功查询数")
    failed_queries: int = Field(..., description="失败查询数")
    success_rate: float = Field(..., description="成功率")
    avg_execution_time_ms: Optional[float] = Field(None, description="平均执行时间")
    total_tokens_used: int = Field(0, description="总共使用的token数")
    
    # 按状态分组统计
    status_distribution: Dict[str, int] = Field(..., description="状态分布")
    
    # 按日期分组统计
    daily_statistics: List[Dict[str, Any]] = Field(..., description="每日统计")
    
    # 按主题分组统计
    theme_statistics: List[Dict[str, Any]] = Field(..., description="主题统计")


class QueryFavoriteBase(BaseModel):
    """查询收藏基础模型"""
    pass


class QueryFavoriteCreate(QueryFavoriteBase):
    """创建查询收藏请求模型"""
    user_id: int = Field(..., description="用户ID")
    history_id: int = Field(..., description="查询历史ID")
    favorite_name: Optional[str] = Field(None, description="收藏名称")
    tags: Optional[List[str]] = Field(None, description="标签列表")


class QueryFavoriteUpdate(BaseModel):
    """更新查询收藏请求模型"""
    favorite_name: Optional[str] = Field(None, description="收藏名称")
    tags: Optional[List[str]] = Field(None, description="标签列表")


class QueryFavoriteResponse(QueryFavoriteBase):
    """查询收藏响应模型"""
    id: int = Field(..., description="收藏记录ID")
    user_id: int = Field(..., description="用户ID")
    history_id: int = Field(..., description="查询历史ID")
    favorite_name: Optional[str] = Field(None, description="收藏名称")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    
    # 关联的查询历史信息
    query_history: QueryHistoryResponse = Field(..., description="查询历史详情")

    class Config:
        from_attributes = True


class RerunQueryRequest(BaseModel):
    """重新执行查询请求模型"""
    history_id: int = Field(..., description="查询历史ID")
    modify_question: Optional[str] = Field(None, description="修改后的问题")
    modify_context: Optional[Dict[str, Any]] = Field(None, description="修改后的上下文")


class RerunQueryResponse(BaseModel):
    """重新执行查询响应模型"""
    task_id: str = Field(..., description="新任务ID")
    original_history_id: int = Field(..., description="原始历史记录ID")
    new_history_id: Optional[int] = Field(None, description="新历史记录ID")
    message: str = Field(..., description="执行消息")


class BatchOperationRequest(BaseModel):
    """批量操作请求模型"""
    history_ids: List[int] = Field(..., description="历史记录ID列表")
    operation: str = Field(..., description="操作类型")


class BatchOperationResponse(BaseModel):
    """批量操作响应模型"""
    success_count: int = Field(..., description="成功数量")
    failure_count: int = Field(..., description="失败数量")
    failed_ids: List[int] = Field([], description="失败的ID列表")
    message: str = Field(..., description="操作消息")