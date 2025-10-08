"""
查询历史服务
处理查询历史的增删改查和相关业务逻辑
"""
import asyncio
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import selectinload

from db.database import get_async_db
from models.nlquery_models import QueryHistory, QueryFavorite
from models.metadata_models import DataTheme, DataTable
from schemas.query_history_schemas import (
    QueryHistoryCreate, QueryHistoryUpdate, QueryHistoryResponse,
    QueryHistoryFilter, QueryHistoryStatistics, QueryFavoriteCreate,
    QueryFavoriteResponse, QueryStatusEnum
)
from utils.logger import get_logger
from utils.exceptions import BusinessException

logger = get_logger(__name__)


class QueryHistoryService:
    """查询历史服务类"""
    
    def __init__(self):
        self.db_dependency = get_async_db
    
    async def create_query_history(
        self, 
        history_data: QueryHistoryCreate,
        db: AsyncSession = None
    ) -> QueryHistory:
        """创建查询历史记录"""
        try:
            if not db:
                async for session in self.db_dependency():
                    db = session
                    break
            
            # 创建历史记录
            history = QueryHistory(
                task_id=history_data.task_id,
                user_id=history_data.user_id,
                user_question=history_data.user_question,
                theme_id=history_data.theme_id,
                table_ids=history_data.table_ids,
                status=history_data.status.value,
                generated_sql=history_data.generated_sql
            )
            
            db.add(history)
            await db.commit()
            await db.refresh(history)
            
            logger.info(f"创建查询历史记录成功: {history.id}")
            return history
            
        except Exception as e:
            await db.rollback()
            logger.error(f"创建查询历史记录失败: {e}", exc_info=True)
            raise BusinessException(f"创建查询历史记录失败: {e}")
    
    async def update_query_history(
        self,
        history_id: int,
        update_data: QueryHistoryUpdate,
        db: AsyncSession = None
    ) -> Optional[QueryHistory]:
        """更新查询历史记录"""
        try:
            if not db:
                async for session in self.db_dependency():
                    db = session
                    break
            
            # 查找历史记录
            stmt = select(QueryHistory).where(QueryHistory.id == history_id)
            result = await db.execute(stmt)
            history = result.scalar_one_or_none()
            
            if not history:
                return None
            
            # 更新字段
            update_fields = update_data.model_dump(exclude_unset=True)
            for field, value in update_fields.items():
                if hasattr(history, field):
                    setattr(history, field, value)
            
            history.updated_at = datetime.now()
            
            await db.commit()
            await db.refresh(history)
            
            logger.info(f"更新查询历史记录成功: {history_id}")
            return history
            
        except Exception as e:
            await db.rollback()
            logger.error(f"更新查询历史记录失败: {e}", exc_info=True)
            raise BusinessException(f"更新查询历史记录失败: {e}")
    
    async def get_user_query_history(
        self,
        filter_params: QueryHistoryFilter,
        page: int = 1,
        page_size: int = 20,
        db: AsyncSession = None
    ) -> Tuple[List[QueryHistoryResponse], int]:
        """获取用户查询历史列表"""
        try:
            if not db:
                async for session in self.db_dependency():
                    db = session
                    break
            
            # 构建查询条件
            conditions = [QueryHistory.user_id == filter_params.user_id]
            
            if filter_params.status:
                conditions.append(QueryHistory.status == filter_params.status.value)
            
            if filter_params.theme_id:
                conditions.append(QueryHistory.theme_id == filter_params.theme_id)
            
            if filter_params.start_date:
                conditions.append(QueryHistory.created_at >= filter_params.start_date)
            
            if filter_params.end_date:
                conditions.append(QueryHistory.created_at <= filter_params.end_date)
            
            if filter_params.keyword:
                keyword_condition = or_(
                    QueryHistory.user_question.ilike(f\"%{filter_params.keyword}%\"),
                    QueryHistory.generated_sql.ilike(f\"%{filter_params.keyword}%\")
                )
                conditions.append(keyword_condition)
            
            # 查询总数
            count_stmt = select(func.count(QueryHistory.id)).where(and_(*conditions))
            count_result = await db.execute(count_stmt)
            total_count = count_result.scalar()
            
            # 查询列表数据
            stmt = (
                select(QueryHistory)
                .options(
                    selectinload(QueryHistory.theme),
                    selectinload(QueryHistory.tables)
                )
                .where(and_(*conditions))
                .order_by(desc(QueryHistory.created_at))
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            
            result = await db.execute(stmt)
            histories = result.scalars().all()
            
            # 检查收藏状态
            if histories:
                history_ids = [h.id for h in histories]
                favorite_stmt = select(QueryFavorite.history_id).where(
                    and_(
                        QueryFavorite.user_id == filter_params.user_id,
                        QueryFavorite.history_id.in_(history_ids)
                    )
                )
                favorite_result = await db.execute(favorite_stmt)
                favorite_ids = set(favorite_result.scalars().all())
            else:
                favorite_ids = set()
            
            # 转换为响应模型
            history_responses = []
            for history in histories:
                response = QueryHistoryResponse(
                    id=history.id,
                    task_id=history.task_id,
                    user_id=history.user_id,
                    user_question=history.user_question,
                    theme_id=history.theme_id,
                    table_ids=history.table_ids,
                    status=QueryStatusEnum(history.status),
                    generated_sql=history.generated_sql,
                    final_sql=history.final_sql,
                    result_count=history.result_count,
                    execution_time_ms=history.execution_time_ms,
                    error_message=history.error_message,
                    llm_tokens_used=history.llm_tokens_used,
                    is_favorite=history.id in favorite_ids,
                    created_at=history.created_at,
                    updated_at=history.updated_at,
                    theme_name=history.theme.theme_name if history.theme else None,
                    table_names=[table.table_name_cn for table in history.tables] if history.tables else None
                )
                history_responses.append(response)
            
            return history_responses, total_count
            
        except Exception as e:
            logger.error(f"获取用户查询历史失败: {e}", exc_info=True)
            raise BusinessException(f"获取用户查询历史失败: {e}")
    
    async def get_query_history_by_id(
        self,
        history_id: int,
        user_id: int,
        db: AsyncSession = None
    ) -> Optional[QueryHistoryResponse]:
        """根据ID获取查询历史详情"""
        try:
            if not db:
                async for session in self.db_dependency():
                    db = session
                    break
            
            # 查询历史记录
            stmt = (
                select(QueryHistory)
                .options(
                    selectinload(QueryHistory.theme),
                    selectinload(QueryHistory.tables)
                )
                .where(
                    and_(
                        QueryHistory.id == history_id,
                        QueryHistory.user_id == user_id
                    )
                )
            )
            
            result = await db.execute(stmt)
            history = result.scalar_one_or_none()
            
            if not history:
                return None
            
            # 检查是否收藏
            favorite_stmt = select(QueryFavorite).where(
                and_(
                    QueryFavorite.user_id == user_id,
                    QueryFavorite.history_id == history_id
                )
            )
            favorite_result = await db.execute(favorite_stmt)
            is_favorite = favorite_result.scalar_one_or_none() is not None
            
            # 转换为响应模型
            response = QueryHistoryResponse(
                id=history.id,
                task_id=history.task_id,
                user_id=history.user_id,
                user_question=history.user_question,
                theme_id=history.theme_id,
                table_ids=history.table_ids,
                status=QueryStatusEnum(history.status),
                generated_sql=history.generated_sql,
                final_sql=history.final_sql,
                result_count=history.result_count,
                execution_time_ms=history.execution_time_ms,
                error_message=history.error_message,
                llm_tokens_used=history.llm_tokens_used,
                is_favorite=is_favorite,
                created_at=history.created_at,
                updated_at=history.updated_at,
                theme_name=history.theme.theme_name if history.theme else None,
                table_names=[table.table_name_cn for table in history.tables] if history.tables else None
            )
            
            return response
            
        except Exception as e:
            logger.error(f"获取查询历史详情失败: {e}", exc_info=True)
            raise BusinessException(f"获取查询历史详情失败: {e}")
    
    async def rerun_query_from_history(
        self,
        history_id: int,
        user_id: int,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """从历史记录重新执行查询"""
        try:
            # 获取历史记录
            history = await self.get_query_history_by_id(history_id, user_id, db)
            if not history:
                raise BusinessException("查询历史不存在")
            
            # TODO: 集成查询执行服务，重新提交查询任务
            # 这里应该调用查询服务来重新执行查询
            from services.nl2sql.query_coordinator import QueryCoordinator
            
            coordinator = QueryCoordinator()
            
            # 重新提交查询
            task_result = await coordinator.submit_query(
                user_id=user_id,
                user_question=history.user_question,
                theme_id=history.theme_id,
                table_ids=history.table_ids,
                context={"rerun_from_history": history_id}
            )
            
            return task_result
            
        except Exception as e:
            logger.error(f"重新执行查询失败: {e}", exc_info=True)
            raise BusinessException(f"重新执行查询失败: {e}")
    
    async def delete_query_history(
        self,
        history_id: int,
        user_id: int,
        db: AsyncSession = None
    ) -> bool:
        """删除查询历史"""
        try:
            if not db:
                async for session in self.db_dependency():
                    db = session
                    break
            
            # 查找并删除历史记录
            stmt = select(QueryHistory).where(
                and_(
                    QueryHistory.id == history_id,
                    QueryHistory.user_id == user_id
                )
            )
            result = await db.execute(stmt)
            history = result.scalar_one_or_none()
            
            if not history:
                return False
            
            # 删除相关收藏记录
            favorite_stmt = select(QueryFavorite).where(QueryFavorite.history_id == history_id)
            favorite_result = await db.execute(favorite_stmt)
            favorites = favorite_result.scalars().all()
            
            for favorite in favorites:
                await db.delete(favorite)
            
            # 删除历史记录
            await db.delete(history)
            await db.commit()
            
            logger.info(f"删除查询历史记录成功: {history_id}")
            return True
            
        except Exception as e:
            await db.rollback()
            logger.error(f"删除查询历史记录失败: {e}", exc_info=True)
            raise BusinessException(f"删除查询历史记录失败: {e}")
    
    async def batch_delete_query_history(
        self,
        history_ids: List[int],
        user_id: int,
        db: AsyncSession = None
    ) -> int:
        """批量删除查询历史"""
        try:
            if not db:
                async for session in self.db_dependency():
                    db = session
                    break
            
            deleted_count = 0
            
            for history_id in history_ids:
                success = await self.delete_query_history(history_id, user_id, db)
                if success:
                    deleted_count += 1
            
            logger.info(f"批量删除查询历史记录: {deleted_count}/{len(history_ids)}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"批量删除查询历史记录失败: {e}", exc_info=True)
            raise BusinessException(f"批量删除查询历史记录失败: {e}")
    
    async def get_query_statistics(
        self,
        user_id: int,
        start_date: datetime,
        end_date: datetime,
        db: AsyncSession = None
    ) -> QueryHistoryStatistics:
        """获取查询统计信息"""
        try:
            if not db:
                async for session in self.db_dependency():
                    db = session
                    break
            
            # 基础条件
            base_conditions = [
                QueryHistory.user_id == user_id,
                QueryHistory.created_at >= start_date,
                QueryHistory.created_at <= end_date
            ]
            
            # 总查询数
            total_stmt = select(func.count(QueryHistory.id)).where(and_(*base_conditions))
            total_result = await db.execute(total_stmt)
            total_queries = total_result.scalar()
            
            # 成功查询数
            success_stmt = select(func.count(QueryHistory.id)).where(\n                and_(*base_conditions, QueryHistory.status == QueryStatusEnum.COMPLETED.value)\n            )
            success_result = await db.execute(success_stmt)
            successful_queries = success_result.scalar()
            
            # 失败查询数
            failed_stmt = select(func.count(QueryHistory.id)).where(\n                and_(*base_conditions, QueryHistory.status == QueryStatusEnum.FAILED.value)\n            )
            failed_result = await db.execute(failed_stmt)
            failed_queries = failed_result.scalar()
            
            # 成功率
            success_rate = successful_queries / total_queries if total_queries > 0 else 0
            
            # 平均执行时间
            avg_time_stmt = select(func.avg(QueryHistory.execution_time_ms)).where(\n                and_(*base_conditions, QueryHistory.status == QueryStatusEnum.COMPLETED.value)\n            )
            avg_time_result = await db.execute(avg_time_stmt)
            avg_execution_time_ms = avg_time_result.scalar()
            
            # 总token使用量
            tokens_stmt = select(func.sum(QueryHistory.llm_tokens_used)).where(and_(*base_conditions))
            tokens_result = await db.execute(tokens_stmt)
            total_tokens_used = tokens_result.scalar() or 0
            
            # 状态分布
            status_stmt = (
                select(QueryHistory.status, func.count(QueryHistory.id))
                .where(and_(*base_conditions))
                .group_by(QueryHistory.status)
            )
            status_result = await db.execute(status_stmt)
            status_distribution = {status: count for status, count in status_result.fetchall()}
            
            # TODO: 实现每日统计和主题统计
            daily_statistics = []
            theme_statistics = []
            
            statistics = QueryHistoryStatistics(
                total_queries=total_queries,
                successful_queries=successful_queries,
                failed_queries=failed_queries,
                success_rate=success_rate,
                avg_execution_time_ms=avg_execution_time_ms,
                total_tokens_used=total_tokens_used,
                status_distribution=status_distribution,
                daily_statistics=daily_statistics,
                theme_statistics=theme_statistics
            )
            
            return statistics
            
        except Exception as e:
            logger.error(f"获取查询统计信息失败: {e}", exc_info=True)
            raise BusinessException(f"获取查询统计信息失败: {e}")
    
    async def add_to_favorites(
        self,
        history_id: int,
        user_id: int,
        favorite_name: Optional[str] = None,
        db: AsyncSession = None
    ) -> QueryFavoriteResponse:
        """添加查询到收藏夹"""
        try:
            if not db:
                async for session in self.db_dependency():
                    db = session
                    break
            
            # 检查是否已经收藏
            existing_stmt = select(QueryFavorite).where(
                and_(
                    QueryFavorite.user_id == user_id,
                    QueryFavorite.history_id == history_id
                )
            )
            existing_result = await db.execute(existing_stmt)
            existing_favorite = existing_result.scalar_one_or_none()
            
            if existing_favorite:
                raise BusinessException("该查询已在收藏夹中")
            
            # 创建收藏记录
            favorite = QueryFavorite(
                user_id=user_id,
                history_id=history_id,
                favorite_name=favorite_name
            )
            
            db.add(favorite)
            await db.commit()
            await db.refresh(favorite)
            
            # 获取详细信息
            history_detail = await self.get_query_history_by_id(history_id, user_id, db)
            
            response = QueryFavoriteResponse(
                id=favorite.id,
                user_id=favorite.user_id,
                history_id=favorite.history_id,
                favorite_name=favorite.favorite_name,
                tags=favorite.tags,
                created_at=favorite.created_at,
                updated_at=favorite.updated_at,
                query_history=history_detail
            )
            
            logger.info(f"添加收藏成功: {favorite.id}")
            return response
            
        except Exception as e:
            await db.rollback()
            logger.error(f"添加收藏失败: {e}", exc_info=True)
            raise BusinessException(f"添加收藏失败: {e}")
    
    async def remove_from_favorites(
        self,
        history_id: int,
        user_id: int,
        db: AsyncSession = None
    ) -> bool:
        """从收藏夹移除查询"""
        try:
            if not db:
                async for session in self.db_dependency():
                    db = session
                    break
            
            # 查找收藏记录
            stmt = select(QueryFavorite).where(
                and_(
                    QueryFavorite.user_id == user_id,
                    QueryFavorite.history_id == history_id
                )
            )
            result = await db.execute(stmt)
            favorite = result.scalar_one_or_none()
            
            if not favorite:
                return False
            
            # 删除收藏记录
            await db.delete(favorite)
            await db.commit()
            
            logger.info(f"移除收藏成功: history_id={history_id}")
            return True
            
        except Exception as e:
            await db.rollback()
            logger.error(f"移除收藏失败: {e}", exc_info=True)
            raise BusinessException(f"移除收藏失败: {e}")