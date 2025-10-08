"""
角色管理API
"""
from fastapi import APIRouter, Depends, HTTPException, Query as QueryParam
from typing import List, Optional

from utils.logger import get_logger
from utils.permissions import require_permissions, Permissions
from schemas.user_schemas import (
    RoleResponse, RoleCreate, RoleUpdate, RoleWithPermissions,
    PermissionResponse
)
from services.user.role_service import RoleService

logger = get_logger(__name__)
router = APIRouter()


@router.get("/roles", response_model=List[RoleResponse])
async def get_roles(
    page: int = QueryParam(1, ge=1, description="页码"),
    page_size: int = QueryParam(20, ge=1, le=100, description="每页大小"),
    keyword: Optional[str] = QueryParam(None, description="搜索关键词"),
    current_user: dict = Depends(require_permissions(Permissions.ROLE_READ))
):
    """获取角色列表"""
    try:
        role_service = RoleService()
        
        roles, total_count = await role_service.get_roles(
            page=page,
            page_size=page_size,
            keyword=keyword
        )
        
        return {
            "success": True,
            "data": roles,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total_count,
                "pages": (total_count + page_size - 1) // page_size
            }
        }
        
    except Exception as e:
        logger.error(f"获取角色列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取角色列表失败")


@router.get("/roles/{role_id}", response_model=RoleWithPermissions)
async def get_role_detail(
    role_id: int,
    current_user: dict = Depends(require_permissions(Permissions.ROLE_READ))
):
    """获取角色详情"""
    try:
        role_service = RoleService()
        
        role_detail = await role_service.get_role_with_permissions(role_id)
        if not role_detail:
            raise HTTPException(status_code=404, detail="角色不存在")
        
        return {
            "success": True,
            "data": role_detail
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取角色详情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取角色详情失败")


@router.post("/roles", response_model=RoleResponse)
async def create_role(
    role_data: RoleCreate,
    current_user: dict = Depends(require_permissions(Permissions.ROLE_CREATE))
):
    """创建角色"""
    try:
        role_service = RoleService()
        
        # 检查角色名是否已存在
        existing_role = await role_service.get_role_by_name(role_data.role_name)
        if existing_role:
            raise HTTPException(status_code=400, detail="角色名已存在")
        
        # 创建角色
        new_role = await role_service.create_role(role_data)
        
        return {
            "success": True,
            "data": new_role,
            "message": "角色创建成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建角色失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="创建角色失败")


@router.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    role_data: RoleUpdate,
    current_user: dict = Depends(require_permissions(Permissions.ROLE_UPDATE))
):
    """更新角色信息"""
    try:
        role_service = RoleService()
        
        # 检查角色是否存在
        existing_role = await role_service.get_role_by_id(role_id)
        if not existing_role:
            raise HTTPException(status_code=404, detail="角色不存在")
        
        # 更新角色
        updated_role = await role_service.update_role(role_id, role_data)
        
        return {
            "success": True,
            "data": updated_role,
            "message": "角色信息更新成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新角色失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="更新角色失败")


@router.delete("/roles/{role_id}")
async def delete_role(
    role_id: int,
    current_user: dict = Depends(require_permissions(Permissions.ROLE_DELETE))
):
    """删除角色"""
    try:
        role_service = RoleService()
        
        # 检查角色是否被使用
        users_count = await role_service.get_role_users_count(role_id)
        if users_count > 0:
            raise HTTPException(
                status_code=400, 
                detail=f"角色正在被 {users_count} 个用户使用，无法删除"
            )
        
        # 删除角色
        deleted = await role_service.delete_role(role_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="角色不存在")
        
        return {
            "success": True,
            "message": "角色删除成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除角色失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="删除角色失败")


@router.post("/roles/{role_id}/assign-permissions")
async def assign_role_permissions(
    role_id: int,
    permission_ids: List[int],
    current_user: dict = Depends(require_permissions(Permissions.ROLE_UPDATE))
):
    """分配角色权限"""
    try:
        role_service = RoleService()
        
        # 分配权限
        role_with_permissions = await role_service.assign_role_permissions(
            role_id, permission_ids
        )
        if not role_with_permissions:
            raise HTTPException(status_code=404, detail="角色不存在")
        
        return {
            "success": True,
            "data": role_with_permissions,
            "message": "角色权限分配成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"分配角色权限失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="分配角色权限失败")


@router.get("/permissions", response_model=List[PermissionResponse])
async def get_permissions(
    current_user: dict = Depends(require_permissions(Permissions.ROLE_READ))
):
    """获取所有权限列表"""
    try:
        role_service = RoleService()
        
        permissions = await role_service.get_all_permissions()
        
        return {
            "success": True,
            "data": permissions
        }
        
    except Exception as e:
        logger.error(f"获取权限列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取权限列表失败")