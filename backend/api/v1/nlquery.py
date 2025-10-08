"""
自然语言查询 API 路由
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from utils.database import get_db
from utils.exceptions import NLQueryException, ValidationException
from schemas.base import DataResponse, PaginatedResponse
from schemas.nlquery_schemas import (
    QueryTaskCreate, QueryTaskResponse, QueryTaskStatus, QueryTaskResult,
    QuerySuggestion, QueryHistoryResponse, QueryHistoryListParams,
    QueryFavoriteCreate, QueryFavoriteUpdate, QueryFavoriteResponse,
    QueryFeedbackCreate, QueryFeedbackResponse,
    BatchQueryRequest, BatchQueryResponse,
    QueryStatistics, QueryOptimizationSuggestion
)
from services.nl2sql.query_processor import get_query_processor

router = APIRouter()


# ========== 查询任务管理 ==========
@router.post("/submit", response_model=DataResponse[Dict[str, Any]], summary="提交查询任务")
async def submit_query(
    query_data: QueryTaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = 1  # TODO: 从认证中间件获取
):
    """提交自然语言查询任务"""
    try:
        processor = get_query_processor()
        
        result = await processor.submit_query(
            user_question=query_data.user_question,
            user_id=current_user_id,
            selected_theme_id=query_data.selected_theme_id,
            selected_table_ids=query_data.selected_table_ids,
            query_type=query_data.query_type.value
        )
        
        return DataResponse(data=result)
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/status/{task_id}", response_model=DataResponse[QueryTaskStatus], summary="获取查询任务状态")
async def get_query_status(
    task_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取查询任务执行状态"""
    try:
        processor = get_query_processor()
        status = await processor.get_task_status(task_id)
        return DataResponse(data=status)
        
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/result/{task_id}", response_model=DataResponse[QueryTaskResult], summary="获取查询任务结果")
async def get_query_result(
    task_id: str,
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=1000, description="每页大小"),
    db: AsyncSession = Depends(get_db)
):
    """获取查询任务执行结果"""
    try:
        processor = get_query_processor()
        result = await processor.get_task_result(task_id)
        
        # 如果有结果数据，进行分页处理
        if result.get("result_data") and isinstance(result["result_data"], list):
            total_rows = len(result["result_data"])
            start_idx = (page - 1) * size
            end_idx = start_idx + size
            
            result["result_data"] = result["result_data"][start_idx:end_idx]
            result["pagination"] = {
                "page": page,
                "size": size,
                "total": total_rows,
                "pages": (total_rows + size - 1) // size
            }
        
        return DataResponse(data=result)
        
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/cancel/{task_id}", response_model=DataResponse[Dict[str, Any]], summary="取消查询任务")
async def cancel_query(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = 1  # TODO: 从认证中间件获取
):
    """取消正在执行的查询任务"""
    try:
        processor = get_query_processor()
        result = await processor.cancel_task(task_id, current_user_id)
        return DataResponse(data=result)
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/suggestions", response_model=DataResponse[List[QuerySuggestion]], summary="获取查询建议")
async def get_query_suggestions(
    q: str = Query(..., min_length=1, description="部分查询文本"),
    limit: int = Query(5, ge=1, le=10, description="返回数量限制"),
    current_user_id: int = 1,  # TODO: 从认证中间件获取
    db: AsyncSession = Depends(get_db)
):
    """根据输入文本获取查询建议"""
    try:
        processor = get_query_processor()
        suggestions = await processor.get_query_suggestions(q, current_user_id, limit)
        return DataResponse(data=suggestions)
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ========== 批量查询 ==========
@router.post("/batch", response_model=DataResponse[BatchQueryResponse], summary="提交批量查询")
async def submit_batch_query(
    batch_request: BatchQueryRequest,
    background_tasks: BackgroundTasks,
    current_user_id: int = 1,  # TODO: 从认证中间件获取
    db: AsyncSession = Depends(get_db)
):
    """提交批量查询任务"""
    try:
        import uuid
        batch_id = str(uuid.uuid4())
        task_ids = []
        
        processor = get_query_processor()
        
        # 逐个提交查询任务
        for query_data in batch_request.queries:
            result = await processor.submit_query(
                user_question=query_data.user_question,
                user_id=current_user_id,
                selected_theme_id=query_data.selected_theme_id,
                selected_table_ids=query_data.selected_table_ids,
                query_type=query_data.query_type.value
            )
            task_ids.append(result["task_id"])
        
        batch_response = BatchQueryResponse(
            batch_id=batch_id,
            batch_name=batch_request.batch_name,
            task_ids=task_ids,
            total_tasks=len(task_ids),
            completed_tasks=0,
            failed_tasks=0,
            batch_status="running"
        )
        
        return DataResponse(data=batch_response)
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/batch/{batch_id}", response_model=DataResponse[BatchQueryResponse], summary="获取批量查询状态")
async def get_batch_status(
    batch_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取批量查询执行状态"""
    # TODO: 实现批量查询状态跟踪
    return DataResponse(data={
        "batch_id": batch_id,
        "message": "批量查询状态跟踪功能开发中..."
    })


# ========== 查询历史 ==========
@router.get("/history", response_model=PaginatedResponse[QueryHistoryResponse], summary="获取查询历史")
async def get_query_history(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页大小"),
    keyword: str = Query(None, description="搜索关键词"),
    task_status: str = Query(None, description="任务状态"),
    category: str = Query(None, description="查询分类"),
    start_date: str = Query(None, description="开始日期"),
    end_date: str = Query(None, description="结束日期"),
    current_user_id: int = 1,  # TODO: 从认证中间件获取
    db: AsyncSession = Depends(get_db)
):
    """获取用户查询历史记录"""
    # TODO: 实现查询历史功能
    from schemas.base import PaginatedData
    empty_result = PaginatedData.create([], 0, page, size)
    return PaginatedResponse(data=empty_result)


@router.post("/history/{history_id}/rerun", response_model=DataResponse[Dict[str, Any]], summary="重新执行历史查询")
async def rerun_history_query(
    history_id: int,
    current_user_id: int = 1,  # TODO: 从认证中间件获取
    db: AsyncSession = Depends(get_db)
):
    """重新执行历史查询"""
    # TODO: 实现历史查询重新执行功能
    return DataResponse(data={"message": "历史查询重新执行功能开发中..."})


# ========== 收藏查询 ==========
@router.post("/favorites", response_model=DataResponse[QueryFavoriteResponse], summary="添加收藏查询")
async def create_favorite_query(
    favorite_data: QueryFavoriteCreate,
    current_user_id: int = 1,  # TODO: 从认证中间件获取
    db: AsyncSession = Depends(get_db)
):
    """添加查询到收藏夹"""
    # TODO: 实现收藏查询功能
    return DataResponse(data={"message": "收藏查询功能开发中..."})


@router.get("/favorites", response_model=PaginatedResponse[QueryFavoriteResponse], summary="获取收藏查询列表")
async def get_favorite_queries(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页大小"),
    folder_name: str = Query(None, description="文件夹名称"),
    keyword: str = Query(None, description="搜索关键词"),
    current_user_id: int = 1,  # TODO: 从认证中间件获取
    db: AsyncSession = Depends(get_db)
):
    """获取用户收藏的查询列表"""
    # TODO: 实现收藏查询列表功能
    from schemas.base import PaginatedData
    empty_result = PaginatedData.create([], 0, page, size)
    return PaginatedResponse(data=empty_result)


@router.put("/favorites/{favorite_id}", response_model=DataResponse[QueryFavoriteResponse], summary="更新收藏查询")
async def update_favorite_query(
    favorite_id: int,
    favorite_data: QueryFavoriteUpdate,
    current_user_id: int = 1,  # TODO: 从认证中间件获取
    db: AsyncSession = Depends(get_db)
):
    """更新收藏查询信息"""
    # TODO: 实现更新收藏查询功能
    return DataResponse(data={"message": "更新收藏查询功能开发中..."})


@router.delete("/favorites/{favorite_id}", response_model=DataResponse[bool], summary="删除收藏查询")
async def delete_favorite_query(
    favorite_id: int,
    current_user_id: int = 1,  # TODO: 从认证中间件获取
    db: AsyncSession = Depends(get_db)
):
    """删除收藏查询"""
    # TODO: 实现删除收藏查询功能
    return DataResponse(data=True)


@router.post("/favorites/{favorite_id}/execute", response_model=DataResponse[Dict[str, Any]], summary="执行收藏查询")
async def execute_favorite_query(
    favorite_id: int,
    current_user_id: int = 1,  # TODO: 从认证中间件获取
    db: AsyncSession = Depends(get_db)
):
    """执行收藏的查询"""
    # TODO: 实现执行收藏查询功能
    return DataResponse(data={"message": "执行收藏查询功能开发中..."})


# ========== 查询反馈 ==========
@router.post("/feedback", response_model=DataResponse[QueryFeedbackResponse], summary="提交查询反馈")
async def submit_query_feedback(
    feedback_data: QueryFeedbackCreate,
    current_user_id: int = 1,  # TODO: 从认证中间件获取
    db: AsyncSession = Depends(get_db)
):
    """提交查询结果反馈"""
    # TODO: 实现查询反馈功能
    return DataResponse(data={"message": "查询反馈功能开发中..."})


@router.get("/feedback", response_model=PaginatedResponse[QueryFeedbackResponse], summary="获取查询反馈列表")
async def get_query_feedback(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页大小"),
    feedback_type: str = Query(None, description="反馈类型"),
    is_processed: bool = Query(None, description="是否已处理"),
    db: AsyncSession = Depends(get_db)
):
    """获取查询反馈列表（管理员功能）"""
    # TODO: 实现查询反馈列表功能
    from schemas.base import PaginatedData
    empty_result = PaginatedData.create([], 0, page, size)
    return PaginatedResponse(data=empty_result)


# ========== 查询统计和分析 ==========
@router.get("/statistics", response_model=DataResponse[QueryStatistics], summary="获取查询统计信息")
async def get_query_statistics(
    start_date: str = Query(None, description="开始日期"),
    end_date: str = Query(None, description="结束日期"),
    current_user_id: int = 1,  # TODO: 从认证中间件获取
    db: AsyncSession = Depends(get_db)
):
    """获取用户查询统计信息"""
    # TODO: 实现查询统计功能
    mock_statistics = QueryStatistics(
        total_queries=0,
        successful_queries=0,
        failed_queries=0,
        success_rate=0.0,
        avg_execution_time_ms=0.0,
        most_used_tables=[],
        popular_questions=[],
        daily_query_counts=[]
    )
    return DataResponse(data=mock_statistics)


@router.get("/optimization-suggestions", response_model=DataResponse[List[QueryOptimizationSuggestion]], summary="获取查询优化建议")
async def get_optimization_suggestions(
    current_user_id: int = 1,  # TODO: 从认证中间件获取
    db: AsyncSession = Depends(get_db)
):
    """获取查询优化建议"""
    # TODO: 实现查询优化建议功能
    mock_suggestions = [
        QueryOptimizationSuggestion(
            suggestion_type="performance",
            priority="medium",
            title="优化查询性能",
            description="建议在查询中添加时间范围限制以提高性能",
            estimated_improvement="可提升查询速度50%",
            implementation_steps=["添加时间过滤条件", "使用合适的索引", "限制返回行数"]
        )
    ]
    return DataResponse(data=mock_suggestions)


# ========== 系统状态 ==========
@router.get("/system/status", response_model=DataResponse[Dict[str, Any]], summary="获取查询系统状态")
async def get_query_system_status(
    db: AsyncSession = Depends(get_db)
):
    """获取查询系统运行状态"""
    try:
        processor = get_query_processor()
        
        status = {
            "active_tasks": processor.get_active_tasks_count(),
            "system_health": "healthy",
            "last_check": "now",
            "version": "1.0.0"
        }
        
        return DataResponse(data=status)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/system/cleanup", response_model=DataResponse[Dict[str, Any]], summary="清理完成的任务")
async def cleanup_completed_tasks(
    max_age_hours: int = Query(24, ge=1, le=168, description="任务最大保留时间(小时)"),
    db: AsyncSession = Depends(get_db)
):
    """清理已完成的查询任务"""
    try:
        processor = get_query_processor()
        processor.cleanup_completed_tasks(max_age_hours)
        
        return DataResponse(data={
            "message": f"已清理超过 {max_age_hours} 小时的完成任务",
            "max_age_hours": max_age_hours
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))