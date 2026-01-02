"""
实体管理API路由
提供部门和角色的CRUD操作接口
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from models.db_base import get_db_session
from models.permission_models import SystemEntity, EntityType
from services.permission_service import EntityService
from middleware.auth_middleware import require_admin_role, get_current_user
from services.token_service import UserInfo
from utils.logger import logger

router = APIRouter(prefix="/entities", tags=["实体管理"])


# Pydantic模型定义
class EntityCreateRequest(BaseModel):
    """创建实体请求模型"""
    code: str
    name: str
    type: EntityType
    description: Optional[str] = None


class EntityUpdateRequest(BaseModel):
    """更新实体请求模型"""
    name: Optional[str] = None
    description: Optional[str] = None


class EntityResponse(BaseModel):
    """实体响应模型"""
    id: str
    code: str
    name: str
    type: EntityType
    description: Optional[str]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class EntityListResponse(BaseModel):
    """实体列表响应模型"""
    entities: List[EntityResponse]
    total: int


# API路由定义
@router.post("/", response_model=EntityResponse, status_code=status.HTTP_201_CREATED)
async def create_entity(
    request: EntityCreateRequest,
    admin_user: UserInfo = Depends(require_admin_role)
):
    """
    创建实体（部门或角色）
    
    需要管理员权限
    """
    try:
        with get_db_session() as db:
            entity_service = EntityService(db)
            
            entity = entity_service.create_entity(
                code=request.code,
                name=request.name,
                entity_type=request.type,
                description=request.description
            )
            
            logger.info(f"管理员 {admin_user.user_id} 创建了{request.type.value}: {entity.code}")
            
            return EntityResponse(
                id=entity.id,
                code=entity.code,
                name=entity.name,
                type=entity.type,
                description=entity.description,
                created_at=entity.created_at.isoformat(),
                updated_at=entity.updated_at.isoformat()
            )
            
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"创建实体失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建实体失败"
        )


@router.get("/", response_model=EntityListResponse)
async def list_entities(
    entity_type: Optional[EntityType] = None,
    current_user: UserInfo = Depends(get_current_user)
):
    """
    获取实体列表
    
    可选择按类型过滤（部门或角色）
    """
    try:
        with get_db_session() as db:
            entity_service = EntityService(db)
            
            if entity_type:
                entities = entity_service.get_entities_by_type(entity_type)
            else:
                # 获取所有类型的实体
                departments = entity_service.get_entities_by_type(EntityType.DEPARTMENT)
                roles = entity_service.get_entities_by_type(EntityType.ROLE)
                entities = departments + roles
            
            entity_responses = [
                EntityResponse(
                    id=entity.id,
                    code=entity.code,
                    name=entity.name,
                    type=entity.type,
                    description=entity.description,
                    created_at=entity.created_at.isoformat(),
                    updated_at=entity.updated_at.isoformat()
                )
                for entity in entities
            ]
            
            return EntityListResponse(
                entities=entity_responses,
                total=len(entity_responses)
            )
            
    except Exception as e:
        logger.error(f"获取实体列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取实体列表失败"
        )


@router.get("/{entity_id}", response_model=EntityResponse)
async def get_entity(
    entity_id: str,
    current_user: UserInfo = Depends(get_current_user)
):
    """
    根据ID获取实体详情
    """
    try:
        with get_db_session() as db:
            entity_service = EntityService(db)
            entity = entity_service.repo.get_entity_by_id(entity_id)
            
            if not entity:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"实体 {entity_id} 不存在"
                )
            
            return EntityResponse(
                id=entity.id,
                code=entity.code,
                name=entity.name,
                type=entity.type,
                description=entity.description,
                created_at=entity.created_at.isoformat(),
                updated_at=entity.updated_at.isoformat()
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取实体详情失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取实体详情失败"
        )


@router.put("/{entity_id}", response_model=EntityResponse)
async def update_entity(
    entity_id: str,
    request: EntityUpdateRequest,
    admin_user: UserInfo = Depends(require_admin_role)
):
    """
    更新实体信息
    
    需要管理员权限
    """
    try:
        with get_db_session() as db:
            entity_service = EntityService(db)
            
            entity = entity_service.update_entity(
                entity_id=entity_id,
                name=request.name,
                description=request.description
            )
            
            logger.info(f"管理员 {admin_user.user_id} 更新了实体: {entity.code}")
            
            return EntityResponse(
                id=entity.id,
                code=entity.code,
                name=entity.name,
                type=entity.type,
                description=entity.description,
                created_at=entity.created_at.isoformat(),
                updated_at=entity.updated_at.isoformat()
            )
            
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"更新实体失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新实体失败"
        )


@router.delete("/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entity(
    entity_id: str,
    admin_user: UserInfo = Depends(require_admin_role)
):
    """
    删除实体
    
    需要管理员权限
    会同时删除相关的权限关联
    """
    try:
        with get_db_session() as db:
            entity_service = EntityService(db)
            
            # 先获取实体信息用于日志
            entity = entity_service.repo.get_entity_by_id(entity_id)
            if not entity:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"实体 {entity_id} 不存在"
                )
            
            success = entity_service.delete_entity(entity_id)
            
            if success:
                logger.info(f"管理员 {admin_user.user_id} 删除了实体: {entity.code}")
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"实体 {entity_id} 不存在"
                )
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除实体失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除实体失败"
        )


# 便捷路由：按类型获取实体
@router.get("/departments/", response_model=EntityListResponse)
async def list_departments(
    current_user: UserInfo = Depends(get_current_user)
):
    """获取所有部门"""
    return await list_entities(EntityType.DEPARTMENT, current_user)


@router.get("/roles/", response_model=EntityListResponse)
async def list_roles(
    current_user: UserInfo = Depends(get_current_user)
):
    """获取所有角色"""
    return await list_entities(EntityType.ROLE, current_user)