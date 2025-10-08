"""
自然语言查询相关的 Pydantic Schemas
"""
from pydantic import Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

from .base import (
    BaseSchema, BaseCreateSchema, BaseUpdateSchema, BaseResponseSchema,
    BaseListParams
)
from models.nlquery_models import TaskStatusEnum, QueryTypeEnum, NodeStatusEnum


# ========== 查询任务相关 ==========
class QueryTaskCreate(BaseCreateSchema):
    """提交查询任务请求"""
    user_question: str = Field(..., min_length=1, max_length=1000, description="用户问题")
    query_type: QueryTypeEnum = Field(default=QueryTypeEnum.NATURAL_LANGUAGE, description="查询类型")
    selected_theme_id: Optional[int] = Field(None, description="选择的数据主题ID")
    selected_table_ids: Optional[List[int]] = Field(default=[], description="选择的表ID列表")
    
    @validator('user_question')
    def validate_user_question(cls, v):
        """验证用户问题"""
        if not v.strip():
            raise ValueError('用户问题不能为空')
        return v.strip()


class QueryTaskResponse(BaseResponseSchema):
    """查询任务响应"""
    task_id: str = Field(description="任务UUID")
    user_id: int = Field(description="用户ID")
    user_question: str = Field(description="用户问题")
    query_type: QueryTypeEnum = Field(description="查询类型")
    selected_theme_id: Optional[int] = Field(description="选择的数据主题ID")
    selected_table_ids: Optional[List[int]] = Field(description="选择的表ID列表")
    task_status: TaskStatusEnum = Field(description="任务状态")
    progress_percentage: int = Field(description="进度百分比")
    current_step: Optional[str] = Field(description="当前步骤")
    generated_sql: Optional[str] = Field(description="生成的SQL")
    final_sql: Optional[str] = Field(description="最终执行的SQL")
    execution_result: Optional[Dict[str, Any]] = Field(description="执行结果")
    result_row_count: Optional[int] = Field(description="结果行数")
    result_columns: Optional[List[str]] = Field(description="结果列信息")
    result_data: Optional[List[List[Any]]] = Field(description="结果数据")
    error_message: Optional[str] = Field(description="错误信息")
    error_code: Optional[str] = Field(description="错误代码")
    start_time: Optional[datetime] = Field(description="开始时间")
    end_time: Optional[datetime] = Field(description="结束时间")
    duration_seconds: Optional[int] = Field(description="执行时长(秒)")
    llm_model: Optional[str] = Field(description="使用的LLM模型")
    llm_tokens_used: Optional[int] = Field(description="使用的Token数量")


class QueryTaskStatus(BaseSchema):
    """查询任务状态"""
    task_id: str = Field(description="任务ID")
    status: TaskStatusEnum = Field(description="任务状态")
    current_step: Optional[str] = Field(description="当前步骤") 
    progress_percentage: int = Field(description="进度百分比")
    error_message: Optional[str] = Field(description="错误信息")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")


class QueryTaskResult(BaseSchema):
    """查询任务结果"""
    task_id: str = Field(description="任务ID")
    status: TaskStatusEnum = Field(description="任务状态")
    user_question: Optional[str] = Field(description="用户问题")
    generated_sql: Optional[str] = Field(description="生成的SQL")
    final_sql: Optional[str] = Field(description="最终执行的SQL")
    execution_result: Optional[Dict[str, Any]] = Field(description="执行结果")
    result_row_count: Optional[int] = Field(description="结果行数")
    result_columns: Optional[List[str]] = Field(description="结果列信息")
    result_data: Optional[List[List[Any]]] = Field(description="结果数据")
    error_message: Optional[str] = Field(description="错误信息")
    llm_tokens_used: Optional[int] = Field(description="使用的Token数量")
    node_execution_log: Optional[List[Dict[str, Any]]] = Field(description="节点执行日志")


class QuerySuggestion(BaseSchema):
    """查询建议"""
    question: str = Field(description="建议的问题")
    similarity: float = Field(description="相似度")
    category: str = Field(description="分类")


# ========== 查询历史相关 ==========
class QueryHistoryResponse(BaseResponseSchema):
    """查询历史响应"""
    user_id: int = Field(description="用户ID")
    task_id: str = Field(description="任务UUID")
    user_question: str = Field(description="用户问题")
    generated_sql: Optional[str] = Field(description="生成的SQL")
    task_status: TaskStatusEnum = Field(description="任务状态")
    result_row_count: Optional[int] = Field(description="结果行数")
    execution_time_ms: Optional[int] = Field(description="执行时间(毫秒)")
    tags: Optional[List[str]] = Field(description="标签列表")
    category: Optional[str] = Field(description="查询分类")
    access_count: int = Field(description="访问次数")
    last_accessed_at: Optional[datetime] = Field(description="最后访问时间")


class QueryHistoryListParams(BaseListParams):
    """查询历史列表参数"""
    user_id: Optional[int] = Field(None, description="用户ID")
    task_status: Optional[TaskStatusEnum] = Field(None, description="任务状态")
    category: Optional[str] = Field(None, description="查询分类")
    start_date: Optional[datetime] = Field(None, description="开始日期")
    end_date: Optional[datetime] = Field(None, description="结束日期")


# ========== 收藏查询相关 ==========
class QueryFavoriteCreate(BaseCreateSchema):
    """创建收藏查询请求"""
    favorite_title: str = Field(..., min_length=1, max_length=200, description="收藏标题")
    favorite_description: Optional[str] = Field(None, description="收藏描述")
    user_question: str = Field(..., min_length=1, description="用户问题")
    generated_sql: Optional[str] = Field(None, description="生成的SQL")
    folder_name: Optional[str] = Field(None, max_length=100, description="文件夹名称")
    tags: Optional[List[str]] = Field(default=[], description="标签列表")


class QueryFavoriteUpdate(BaseUpdateSchema):
    """更新收藏查询请求"""
    favorite_title: Optional[str] = Field(None, min_length=1, max_length=200, description="收藏标题")
    favorite_description: Optional[str] = Field(None, description="收藏描述")
    folder_name: Optional[str] = Field(None, max_length=100, description="文件夹名称")
    tags: Optional[List[str]] = Field(None, description="标签列表")


class QueryFavoriteResponse(BaseResponseSchema):
    """收藏查询响应"""
    user_id: int = Field(description="用户ID")
    favorite_title: str = Field(description="收藏标题")
    favorite_description: Optional[str] = Field(description="收藏描述")
    user_question: str = Field(description="用户问题")
    generated_sql: Optional[str] = Field(description="生成的SQL")
    folder_name: Optional[str] = Field(description="文件夹名称")
    tags: List[str] = Field(description="标签列表")
    usage_count: int = Field(description="使用次数")
    last_used_at: Optional[datetime] = Field(description="最后使用时间")


class QueryFavoriteListParams(BaseListParams):
    """收藏查询列表参数"""
    user_id: Optional[int] = Field(None, description="用户ID")
    folder_name: Optional[str] = Field(None, description="文件夹名称")
    tags: Optional[List[str]] = Field(None, description="标签筛选")


# ========== 查询反馈相关 ==========
class QueryFeedbackCreate(BaseCreateSchema):
    """提交查询反馈请求"""
    task_id: int = Field(..., description="任务ID")
    feedback_type: str = Field(..., description="反馈类型(good/bad/suggestion)")
    rating: Optional[int] = Field(None, ge=1, le=5, description="评分(1-5)")
    feedback_content: Optional[str] = Field(None, description="反馈内容")
    sql_accuracy: Optional[int] = Field(None, ge=1, le=5, description="SQL准确性评分")
    result_relevance: Optional[int] = Field(None, ge=1, le=5, description="结果相关性评分")
    response_speed: Optional[int] = Field(None, ge=1, le=5, description="响应速度评分")
    improvement_suggestions: Optional[str] = Field(None, description="改进建议")
    expected_result: Optional[str] = Field(None, description="期望的结果")


class QueryFeedbackResponse(BaseResponseSchema):
    """查询反馈响应"""
    task_id: int = Field(description="任务ID")
    user_id: int = Field(description="用户ID")
    feedback_type: str = Field(description="反馈类型")
    rating: Optional[int] = Field(description="评分")
    feedback_content: Optional[str] = Field(description="反馈内容")
    sql_accuracy: Optional[int] = Field(description="SQL准确性评分")
    result_relevance: Optional[int] = Field(description="结果相关性评分")
    response_speed: Optional[int] = Field(description="响应速度评分")
    improvement_suggestions: Optional[str] = Field(description="改进建议")
    expected_result: Optional[str] = Field(description="期望的结果")
    is_processed: bool = Field(description="是否已处理")
    admin_response: Optional[str] = Field(description="管理员回复")
    processed_at: Optional[datetime] = Field(description="处理时间")


# ========== 查询模板相关 ==========
class QueryTemplateResponse(BaseResponseSchema):
    """查询模板响应"""
    template_name: str = Field(description="模板名称")
    template_description: Optional[str] = Field(description="模板描述")
    category: Optional[str] = Field(description="模板分类")
    question_template: str = Field(description="问题模板")
    sql_template: Optional[str] = Field(description="SQL模板")
    parameters: Optional[Dict[str, Any]] = Field(description="模板参数配置")
    required_tables: Optional[List[str]] = Field(description="需要的表列表")
    required_themes: Optional[List[str]] = Field(description="需要的主题列表")
    usage_count: int = Field(description="使用次数")
    success_rate: Optional[int] = Field(description="成功率(%)")
    is_active: bool = Field(description="是否启用")
    is_public: bool = Field(description="是否公共模板")


# ========== 工作流节点相关 ==========
class WorkflowNodeResponse(BaseSchema):
    """工作流节点响应"""
    node_name: str = Field(description="节点名称")
    node_type: str = Field(description="节点类型")
    node_order: int = Field(description="节点顺序")
    node_status: NodeStatusEnum = Field(description="节点状态")
    start_time: Optional[datetime] = Field(description="开始时间")
    end_time: Optional[datetime] = Field(description="结束时间")
    duration_ms: Optional[int] = Field(description="执行时长(毫秒)")
    input_data: Optional[Dict[str, Any]] = Field(description="输入数据")
    output_data: Optional[Dict[str, Any]] = Field(description="输出数据")
    error_message: Optional[str] = Field(description="错误信息")
    retry_count: int = Field(description="重试次数")


# ========== 批量操作相关 ==========
class BatchQueryRequest(BaseCreateSchema):
    """批量查询请求"""
    queries: List[QueryTaskCreate] = Field(..., min_items=1, max_items=10, description="查询列表")
    batch_name: Optional[str] = Field(None, description="批次名称")


class BatchQueryResponse(BaseSchema):
    """批量查询响应"""
    batch_id: str = Field(description="批次ID")
    batch_name: Optional[str] = Field(description="批次名称")
    task_ids: List[str] = Field(description="任务ID列表")
    total_tasks: int = Field(description="总任务数")
    completed_tasks: int = Field(description="已完成任务数")
    failed_tasks: int = Field(description="失败任务数")
    batch_status: str = Field(description="批次状态")


# ========== 查询统计相关 ==========
class QueryStatistics(BaseSchema):
    """查询统计"""
    total_queries: int = Field(description="总查询数")
    successful_queries: int = Field(description="成功查询数")
    failed_queries: int = Field(description="失败查询数")
    success_rate: float = Field(description="成功率")
    avg_execution_time_ms: float = Field(description="平均执行时间(毫秒)")
    most_used_tables: List[Dict[str, Any]] = Field(description="最常用的表")
    popular_questions: List[Dict[str, Any]] = Field(description="热门问题")
    daily_query_counts: List[Dict[str, Any]] = Field(description="每日查询统计")


# ========== 查询优化建议 ==========
class QueryOptimizationSuggestion(BaseSchema):
    """查询优化建议"""
    suggestion_type: str = Field(description="建议类型")
    priority: str = Field(description="优先级(high/medium/low)")
    title: str = Field(description="建议标题")
    description: str = Field(description="建议描述")
    estimated_improvement: Optional[str] = Field(description="预估改进效果")
    implementation_steps: List[str] = Field(description="实施步骤")