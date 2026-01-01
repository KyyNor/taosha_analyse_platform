"""
权限管理API路由
提供页面管理和权限分配的接口
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from models.db_base import get_db_session
from models.permission_models import SystemPage, SystemEntity, EntityType
from services.permission_service import PageService
from services.page_discovery_service import PageDiscoveryService
from services.permission_assignment_service import PermissionAssignmentService
from middleware.auth_middleware import require_admin_role, get_current_user
from services.token_service import UserInfo
from utils.logger import logger

router = APIRouter(prefix="/api/permissions", tags=["权限管理"])


# Pydantic模型定义
class PageResponse(BaseModel):
    """页面响应模型"""
    id: str
    path: str
    name: str
    description: Optional[str]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class PageListResponse(BaseModel):
    """页面列表响应模型"""
    pages: List[PageResponse]
    total: int


class EntityPermissionResponse(BaseModel):
    """实体权限响应模型"""
    entity_id: str
    entity_code: str
    entity_name: str
    entity_type: str
    pages: List[PageResponse]


class PermissionAssignmentRequest(BaseModel):
    """权限分配请求模型"""
    entity_id: str
    page_ids: List[str]


class BulkPermissionAssignmentRequest(BaseModel):
    """批量权限分配请求模型"""
    assignments: List[PermissionAssignmentRequest]


class PermissionMatrixResponse(BaseModel):
    """权限矩阵响应模型"""
    entities: List[Dict[str, Any]]
    pages: List[Dict[str, Any]]
    matrix: Dict[str, Dict[str, bool]]


class PermissionSummaryResponse(BaseModel):
    """权限摘要响应模型"""
    total_entities: int
    total_pages: int
    total_permissions: int
    departments_count: int
    roles_count: int
    entities_with_permissions: int
    pages_with_permissions: int
    permission_coverage: Dict[str, float]


# 页面管理路由
@router.get("/pages", response_model=PageListResponse)
async def list_pages(
    current_user: UserInfo = Depends(get_current_user)
):
    """获取所有页面列表"""
    try:
        with get_db_session() as db:
            page_service = PageService(db)
            pages = page_service.get_all_pages()
            
            page_responses = [
                PageResponse(
                    id=page.id,
                    path=page.path,
                    name=page.name,
                    description=page.description,
                    created_at=page.created_at.isoformat(),
                    updated_at=page.updated_at.isoformat()
                )
                for page in pages
            ]
            
            return PageListResponse(
                pages=page_responses,
                total=len(page_responses)
            )
            
    except Exception as e:
        logger.error(f"获取页面列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取页面列表失败"
        )


@router.post("/pages/sync", status_code=status.HTTP_200_OK)
async def sync_pages_from_config(
    admin_user: UserInfo = Depends(require_admin_role)
):
    """
    从配置文件同步页面到数据库
    
    需要管理员权限
    """
    try:
        with get_db_session() as db:
            discovery_service = PageDiscoveryService(db)
            count = discovery_service.sync_pages_from_config()
            
            logger.info(f"管理员 {admin_user.user_id} 触发了页面同步，处理了 {count} 个页面")
            
            return {
                "message": "页面同步完成",
                "synced_count": count
            }
            
    except Exception as e:
        logger.error(f"页面同步失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="页面同步失败"
        )


@router.get("/pages/config")
async def get_pages_from_config(
    current_user: UserInfo = Depends(get_current_user)
):
    """获取配置文件中的页面信息"""
    try:
        with get_db_session() as db:
            discovery_service = PageDiscoveryService(db)
            pages_config = discovery_service.get_all_pages_from_config()
            
            return {
                "pages": pages_config,
                "total": len(pages_config)
            }
            
    except Exception as e:
        logger.error(f"获取配置页面信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取配置页面信息失败"
        )


# 权限分配路由
@router.post("/assign", status_code=status.HTTP_200_OK)
async def assign_permissions(
    request: PermissionAssignmentRequest,
    admin_user: UserInfo = Depends(require_admin_role)
):
    """
    为实体分配页面权限
    
    需要管理员权限
    """
    try:
        with get_db_session() as db:
            assignment_service = PermissionAssignmentService(db)
            
            success = assignment_service.assign_pages_to_entity(
                entity_id=request.entity_id,
                page_ids=request.page_ids
            )
            
            if success:
                logger.info(f"管理员 {admin_user.user_id} 为实体 {request.entity_id} 分配了 {len(request.page_ids)} 个页面权限")
                return {
                    "message": "权限分配成功",
                    "entity_id": request.entity_id,
                    "assigned_pages": len(request.page_ids)
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="权限分配失败"
                )
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"权限分配失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="权限分配失败"
        )


@router.post("/assign/bulk", status_code=status.HTTP_200_OK)
async def bulk_assign_permissions(
    request: BulkPermissionAssignmentRequest,
    admin_user: UserInfo = Depends(require_admin_role)
):
    """
    批量分配权限
    
    需要管理员权限
    """
    try:
        with get_db_session() as db:
            assignment_service = PermissionAssignmentService(db)
            
            # 转换请求格式
            assignments = [
                {
                    "entity_id": assignment.entity_id,
                    "page_ids": assignment.page_ids
                }
                for assignment in request.assignments
            ]
            
            result = assignment_service.bulk_assign_permissions(assignments)
            
            logger.info(f"管理员 {admin_user.user_id} 执行了批量权限分配: 成功 {result['success_count']}, 失败 {result['error_count']}")
            
            return result
            
    except Exception as e:
        logger.error(f"批量权限分配失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="批量权限分配失败"
        )


@router.get("/entity/{entity_id}", response_model=EntityPermissionResponse)
async def get_entity_permissions(
    entity_id: str,
    current_user: UserInfo = Depends(get_current_user)
):
    """获取实体的权限页面列表"""
    try:
        with get_db_session() as db:
            assignment_service = PermissionAssignmentService(db)
            
            # 获取实体信息
            entity = assignment_service.repo.get_entity_by_id(entity_id)
            if not entity:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"实体 {entity_id} 不存在"
                )
            
            # 获取权限页面
            pages = assignment_service.get_entity_permissions(entity_id)
            
            page_responses = [
                PageResponse(
                    id=page.id,
                    path=page.path,
                    name=page.name,
                    description=page.description,
                    created_at=page.created_at.isoformat(),
                    updated_at=page.updated_at.isoformat()
                )
                for page in pages
            ]
            
            return EntityPermissionResponse(
                entity_id=entity.id,
                entity_code=entity.code,
                entity_name=entity.name,
                entity_type=entity.type.value,
                pages=page_responses
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取实体权限失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取实体权限失败"
        )


@router.delete("/entity/{entity_id}/page/{page_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_entity_page_permission(
    entity_id: str,
    page_id: str,
    admin_user: UserInfo = Depends(require_admin_role)
):
    """
    移除实体的单个页面权限
    
    需要管理员权限
    """
    try:
        with get_db_session() as db:
            assignment_service = PermissionAssignmentService(db)
            
            success = assignment_service.remove_page_from_entity(entity_id, page_id)
            
            if success:
                logger.info(f"管理员 {admin_user.user_id} 移除了实体 {entity_id} 对页面 {page_id} 的权限")
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="权限不存在"
                )
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"移除页面权限失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="移除页面权限失败"
        )


@router.post("/entity/{entity_id}/page/{page_id}", status_code=status.HTTP_201_CREATED)
async def add_entity_page_permission(
    entity_id: str,
    page_id: str,
    admin_user: UserInfo = Depends(require_admin_role)
):
    """
    为实体添加单个页面权限
    
    需要管理员权限
    """
    try:
        with get_db_session() as db:
            assignment_service = PermissionAssignmentService(db)
            
            success = assignment_service.add_page_to_entity(entity_id, page_id)
            
            if success:
                logger.info(f"管理员 {admin_user.user_id} 为实体 {entity_id} 添加了页面 {page_id} 的权限")
                return {
                    "message": "权限添加成功",
                    "entity_id": entity_id,
                    "page_id": page_id
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="权限添加失败"
                )
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"添加页面权限失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="添加页面权限失败"
        )


@router.get("/matrix", response_model=PermissionMatrixResponse)
async def get_permission_matrix(
    admin_user: UserInfo = Depends(require_admin_role)
):
    """
    获取权限矩阵
    
    需要管理员权限
    """
    try:
        with get_db_session() as db:
            assignment_service = PermissionAssignmentService(db)
            
            # 获取权限矩阵
            matrix = assignment_service.get_permission_matrix()
            
            # 获取实体和页面信息
            all_entities = (assignment_service.repo.get_entities_by_type(EntityType.DEPARTMENT) + 
                          assignment_service.repo.get_entities_by_type(EntityType.ROLE))
            all_pages = assignment_service.repo.get_all_pages()
            
            entities_info = [
                {
                    "id": entity.id,
                    "code": entity.code,
                    "name": entity.name,
                    "type": entity.type.value
                }
                for entity in all_entities
            ]
            
            pages_info = [
                {
                    "id": page.id,
                    "path": page.path,
                    "name": page.name
                }
                for page in all_pages
            ]
            
            return PermissionMatrixResponse(
                entities=entities_info,
                pages=pages_info,
                matrix=matrix
            )
            
    except Exception as e:
        logger.error(f"获取权限矩阵失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取权限矩阵失败"
        )


@router.get("/summary", response_model=PermissionSummaryResponse)
async def get_permission_summary(
    current_user: UserInfo = Depends(get_current_user)
):
    """获取权限分配摘要信息"""
    try:
        with get_db_session() as db:
            assignment_service = PermissionAssignmentService(db)
            summary = assignment_service.get_permission_summary()
            
            return PermissionSummaryResponse(**summary)
            
    except Exception as e:
        logger.error(f"获取权限摘要失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取权限摘要失败"
        )


@router.post("/copy/{source_entity_id}/{target_entity_id}", status_code=status.HTTP_200_OK)
async def copy_permissions(
    source_entity_id: str,
    target_entity_id: str,
    admin_user: UserInfo = Depends(require_admin_role)
):
    """
    复制权限从一个实体到另一个实体
    
    需要管理员权限
    """
    try:
        with get_db_session() as db:
            assignment_service = PermissionAssignmentService(db)
            
            success = assignment_service.copy_permissions(source_entity_id, target_entity_id)
            
            if success:
                logger.info(f"管理员 {admin_user.user_id} 复制权限从实体 {source_entity_id} 到 {target_entity_id}")
                return {
                    "message": "权限复制成功",
                    "source_entity_id": source_entity_id,
                    "target_entity_id": target_entity_id
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="权限复制失败"
                )
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"权限复制失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="权限复制失败"
        )