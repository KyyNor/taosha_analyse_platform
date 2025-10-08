"""
查询历史管理API
"""
from fastapi import APIRouter, Depends, HTTPException, Query as QueryParam
from typing import List, Optional
from datetime import datetime, timedelta

from utils.logger import get_logger
from utils.permissions import get_current_user
from schemas.nlquery_schemas import (
    QueryHistoryResponse, QueryHistoryFilter, 
    QueryHistoryCreate, QueryHistoryUpdate,
    QueryHistoryStatistics
)
from services.query_history.query_history_service import QueryHistoryService

logger = get_logger(__name__)
router = APIRouter()


@router.get("/history", response_model=List[QueryHistoryResponse])
async def get_query_history(
    page: int = QueryParam(1, ge=1, description="页码"),
    page_size: int = QueryParam(20, ge=1, le=100, description="每页大小"),
    status: Optional[str] = QueryParam(None, description="查询状态筛选"),
    theme_id: Optional[int] = QueryParam(None, description="数据主题筛选"),
    start_date: Optional[datetime] = QueryParam(None, description="开始时间"),
    end_date: Optional[datetime] = QueryParam(None, description="结束时间"),
    keyword: Optional[str] = QueryParam(None, description="关键词搜索"),
    current_user: dict = Depends(get_current_user)
):
    """获取查询历史列表"""
    try:
        # 构建筛选条件
        filter_params = QueryHistoryFilter(
            user_id=current_user["id"],
            status=status,
            theme_id=theme_id,
            start_date=start_date,
            end_date=end_date,
            keyword=keyword
        )
        
        history_service = QueryHistoryService()
        
        # 获取历史记录
        history_list, total_count = await history_service.get_user_query_history(
            filter_params=filter_params,
            page=page,
            page_size=page_size
        )
        
        return {
            "success": True,
            "data": history_list,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total_count,
                "pages": (total_count + page_size - 1) // page_size
            }
        }
        
    except Exception as e:
        logger.error(f"获取查询历史失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取查询历史失败")


@router.get("/history/{history_id}", response_model=QueryHistoryResponse)
async def get_query_history_detail(
    history_id: int,
    current_user: dict = Depends(get_current_user)
):
    """获取查询历史详情"""
    try:
        history_service = QueryHistoryService()
        
        # 获取历史记录详情
        history_detail = await history_service.get_query_history_by_id(
            history_id=history_id,
            user_id=current_user["id"]
        )
        
        if not history_detail:
            raise HTTPException(status_code=404, detail="查询历史不存在")
        
        return {
            "success": True,
            "data": history_detail
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取查询历史详情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取查询历史详情失败")


@router.post("/history/{history_id}/rerun")
async def rerun_query_from_history(
    history_id: int,
    current_user: dict = Depends(get_current_user)
):
    """重新执行历史查询"""
    try:
        history_service = QueryHistoryService()
        
        # 获取历史记录
        history_detail = await history_service.get_query_history_by_id(
            history_id=history_id,
            user_id=current_user["id"]
        )
        
        if not history_detail:
            raise HTTPException(status_code=404, detail="查询历史不存在")
        
        # 重新执行查询
        new_task = await history_service.rerun_query_from_history(
            history_id=history_id,
            user_id=current_user["id"]
        )
        
        return {
            "success": True,
            "data": {
                "task_id": new_task.task_id,
                "message": "查询已重新提交执行"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重新执行查询失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="重新执行查询失败")


@router.delete("/history/{history_id}")
async def delete_query_history(
    history_id: int,
    current_user: dict = Depends(get_current_user)
):
    """删除查询历史"""
    try:
        history_service = QueryHistoryService()
        
        # 删除历史记录
        deleted = await history_service.delete_query_history(
            history_id=history_id,
            user_id=current_user["id"]
        )
        
        if not deleted:
            raise HTTPException(status_code=404, detail="查询历史不存在")
        
        return {
            "success": True,
            "message": "查询历史已删除"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除查询历史失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="删除查询历史失败")


@router.post("/history/batch-delete")
async def batch_delete_query_history(
    history_ids: List[int],
    current_user: dict = Depends(get_current_user)
):
    """批量删除查询历史"""
    try:
        history_service = QueryHistoryService()
        
        # 批量删除历史记录
        deleted_count = await history_service.batch_delete_query_history(
            history_ids=history_ids,
            user_id=current_user["id"]
        )
        
        return {
            "success": True,
            "data": {
                "deleted_count": deleted_count,
                "message": f"已删除 {deleted_count} 条查询历史"
            }
        }
        
    except Exception as e:
        logger.error(f"批量删除查询历史失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="批量删除查询历史失败")


@router.get("/history/statistics", response_model=QueryHistoryStatistics)
async def get_query_history_statistics(
    days: int = QueryParam(30, ge=1, le=365, description="统计天数"),
    current_user: dict = Depends(get_current_user)
):
    """获取查询历史统计信息"""
    try:
        history_service = QueryHistoryService()
        
        # 计算时间范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # 获取统计信息
        statistics = await history_service.get_query_statistics(
            user_id=current_user["id"],
            start_date=start_date,
            end_date=end_date
        )
        
        return {
            "success": True,
            "data": statistics
        }
        
    except Exception as e:
        logger.error(f"获取查询统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取查询统计失败")


@router.post("/history/{history_id}/favorite")
async def add_query_to_favorites(
    history_id: int,
    current_user: dict = Depends(get_current_user)
):
    """添加查询到收藏夹"""
    try:
        history_service = QueryHistoryService()
        
        # 添加到收藏夹
        favorite = await history_service.add_to_favorites(
            history_id=history_id,
            user_id=current_user["id"]
        )
        
        return {
            "success": True,
            "data": favorite,
            "message": "已添加到收藏夹"
        }
        
    except Exception as e:
        logger.error(f"添加收藏失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="添加收藏失败")


@router.delete("/history/{history_id}/favorite")
async def remove_query_from_favorites(
    history_id: int,
    current_user: dict = Depends(get_current_user)
):
    """从收藏夹移除查询"""
    try:
        history_service = QueryHistoryService()
        
        # 从收藏夹移除
        removed = await history_service.remove_from_favorites(
            history_id=history_id,
            user_id=current_user["id"]
        )
        
        if not removed:
            raise HTTPException(status_code=404, detail="收藏记录不存在")
        
        return {
            "success": True,
            "message": "已从收藏夹移除"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"移除收藏失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="移除收藏失败")