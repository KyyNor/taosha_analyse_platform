"""
用户管理API
"""
from fastapi import APIRouter, Depends, HTTPException, Query as QueryParam
from typing import List, Optional
from datetime import datetime

from utils.logger import get_logger
from utils.permissions import (
    get_current_user, require_permissions, require_superuser,
    Permissions
)
from schemas.user_schemas import (
    UserResponse, UserCreate, UserUpdate, 
    UserWithRoles, ChangePasswordRequest
)
from services.user.user_service import UserService

logger = get_logger(__name__)
router = APIRouter()


@router.get("/users", response_model=List[UserResponse])
async def get_users(
    page: int = QueryParam(1, ge=1, description="页码"),
    page_size: int = QueryParam(20, ge=1, le=100, description="每页大小"),
    keyword: Optional[str] = QueryParam(None, description="搜索关键词"),
    is_active: Optional[bool] = QueryParam(None, description="用户状态筛选"),
    current_user: dict = Depends(require_permissions(Permissions.USER_READ))
):
    """获取用户列表"""
    try:
        user_service = UserService()
        
        users, total_count = await user_service.get_users(
            page=page,
            page_size=page_size,
            keyword=keyword,
            is_active=is_active
        )
        
        return {
            "success": True,
            "data": users,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total_count,
                "pages": (total_count + page_size - 1) // page_size
            }
        }
        
    except Exception as e:
        logger.error(f"获取用户列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取用户列表失败")


@router.get("/users/{user_id}", response_model=UserWithRoles)
async def get_user_detail(
    user_id: int,
    current_user: dict = Depends(require_permissions(Permissions.USER_READ))
):
    """获取用户详情"""
    try:
        user_service = UserService()
        
        user_detail = await user_service.get_user_with_roles(user_id)
        if not user_detail:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        return {
            "success": True,
            "data": user_detail
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户详情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取用户详情失败")


@router.post("/users", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    current_user: dict = Depends(require_permissions(Permissions.USER_CREATE))
):
    """创建用户"""
    try:
        user_service = UserService()
        
        # 检查用户名和邮箱是否已存在
        existing_user = await user_service.get_user_by_username(user_data.username)
        if existing_user:
            raise HTTPException(status_code=400, detail="用户名已存在")
        
        existing_email = await user_service.get_user_by_email(user_data.email)
        if existing_email:
            raise HTTPException(status_code=400, detail="邮箱已存在")
        
        # 创建用户
        new_user = await user_service.create_user(user_data)
        
        return {
            "success": True,
            "data": new_user,
            "message": "用户创建成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建用户失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="创建用户失败")


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: dict = Depends(require_permissions(Permissions.USER_UPDATE))
):
    """更新用户信息"""
    try:
        user_service = UserService()
        
        # 检查用户是否存在
        existing_user = await user_service.get_user_by_id(user_id)
        if not existing_user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 更新用户
        updated_user = await user_service.update_user(user_id, user_data)
        
        return {
            "success": True,
            "data": updated_user,
            "message": "用户信息更新成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新用户失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="更新用户失败")


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: dict = Depends(require_permissions(Permissions.USER_DELETE))
):
    """删除用户"""
    try:
        # 防止删除自己
        if user_id == current_user["id"]:
            raise HTTPException(status_code=400, detail="不能删除自己")
        
        user_service = UserService()
        
        # 软删除用户
        deleted = await user_service.delete_user(user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        return {
            "success": True,
            "message": "用户删除成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除用户失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="删除用户失败")


@router.post("/users/{user_id}/reset-password")
async def reset_user_password(
    user_id: int,
    current_user: dict = Depends(require_permissions(Permissions.USER_UPDATE))
):
    """重置用户密码"""
    try:
        user_service = UserService()
        
        # 生成新密码
        new_password = await user_service.reset_user_password(user_id)
        
        return {
            "success": True,
            "data": {
                "new_password": new_password,
                "message": "密码重置成功，请及时通知用户修改密码"
            }
        }
        
    except Exception as e:
        logger.error(f"重置用户密码失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="重置用户密码失败")


@router.post("/users/{user_id}/toggle-status")
async def toggle_user_status(
    user_id: int,
    current_user: dict = Depends(require_permissions(Permissions.USER_UPDATE))
):
    """切换用户状态（启用/禁用）"""
    try:
        # 防止禁用自己
        if user_id == current_user["id"]:
            raise HTTPException(status_code=400, detail="不能禁用自己")
        
        user_service = UserService()
        
        user = await user_service.toggle_user_status(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        status_text = "启用" if user.is_active else "禁用"
        
        return {
            "success": True,
            "data": user,
            "message": f"用户已{status_text}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"切换用户状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="切换用户状态失败")


@router.post("/users/{user_id}/assign-roles")
async def assign_user_roles(
    user_id: int,
    role_ids: List[int],
    current_user: dict = Depends(require_permissions(Permissions.USER_UPDATE))
):
    """分配用户角色"""
    try:
        user_service = UserService()
        
        # 分配角色
        user_with_roles = await user_service.assign_user_roles(user_id, role_ids)
        if not user_with_roles:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        return {
            "success": True,
            "data": user_with_roles,
            "message": "用户角色分配成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"分配用户角色失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="分配用户角色失败")


# ========== 当前用户相关接口 ==========

@router.get("/profile", response_model=UserWithRoles)
async def get_current_user_profile(
    current_user: dict = Depends(get_current_user)
):
    """获取当前用户信息"""
    try:
        user_service = UserService()
        
        user_detail = await user_service.get_user_with_roles(current_user["id"])
        
        return {
            "success": True,
            "data": user_detail
        }
        
    except Exception as e:
        logger.error(f"获取当前用户信息失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取用户信息失败")


@router.put("/profile")
async def update_current_user_profile(
    user_data: UserUpdate,
    current_user: dict = Depends(get_current_user)
):
    """更新当前用户信息"""
    try:
        user_service = UserService()
        
        # 只允许更新部分字段
        allowed_fields = {"full_name", "email"}
        update_data = {k: v for k, v in user_data.model_dump(exclude_unset=True).items() 
                      if k in allowed_fields}
        
        if not update_data:
            raise HTTPException(status_code=400, detail="没有可更新的字段")
        
        # 检查邮箱是否重复
        if "email" in update_data:
            existing_email = await user_service.get_user_by_email(update_data["email"])
            if existing_email and existing_email.id != current_user["id"]:
                raise HTTPException(status_code=400, detail="邮箱已被使用")
        
        updated_user = await user_service.update_user(
            current_user["id"], 
            UserUpdate(**update_data)
        )
        
        return {
            "success": True,
            "data": updated_user,
            "message": "个人信息更新成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新个人信息失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="更新个人信息失败")


@router.post("/change-password")
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user)
):
    """修改密码"""
    try:
        user_service = UserService()
        
        # 验证旧密码并更改密码
        success = await user_service.change_user_password(
            current_user["id"],
            password_data.old_password,
            password_data.new_password
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="原密码错误")
        
        return {
            "success": True,
            "message": "密码修改成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"修改密码失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="修改密码失败")