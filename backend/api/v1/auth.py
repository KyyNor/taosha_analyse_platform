"""
认证相关API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta

from utils.logger import get_logger
from utils.simple_permissions import permission_checker, get_current_user
from schemas.user_schemas import LoginResponse, UserWithRoles
from services.user.user_service import UserService
from config.settings import get_settings

logger = get_logger(__name__)
router = APIRouter()
settings = get_settings()


@router.post("/login", response_model=LoginResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """用户登录"""
    try:
        user_service = UserService()
        
        # 认证用户
        user = await user_service.authenticate_user(
            username=form_data.username,
            password=form_data.password
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 生成访问令牌
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = permission_checker.create_access_token(
            data={"sub": user.id, "username": user.username},
            expires_delta=access_token_expires
        )
        
        # 获取用户完整信息
        user_info = await user_service.get_user_with_roles(user.id)
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": user_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"用户登录失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登录失败"
        )


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """用户登出"""
    try:
        # TODO: 实现token黑名单机制
        # 目前只是简单返回成功，实际应该将token加入黑名单
        
        logger.info(f"用户登出: {current_user['username']}")
        
        return {
            "success": True,
            "message": "登出成功"
        }
        
    except Exception as e:
        logger.error(f"用户登出失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登出失败"
        )


@router.get("/me", response_model=UserWithRoles)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """获取当前用户信息"""
    try:
        user_service = UserService()
        
        user_info = await user_service.get_user_with_roles(current_user["id"])
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        
        return {
            "success": True,
            "data": user_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取当前用户信息失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户信息失败"
        )


@router.post("/refresh-token")
async def refresh_token(current_user: dict = Depends(get_current_user)):
    """刷新访问令牌"""
    try:
        # 生成新的访问令牌
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = permission_checker.create_access_token(
            data={"sub": current_user["id"], "username": current_user["username"]},
            expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
        
    except Exception as e:
        logger.error(f"刷新令牌失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="刷新令牌失败"
        )


@router.get("/check-token")
async def check_token(current_user: dict = Depends(get_current_user)):
    """检查令牌有效性"""
    return {
        "success": True,
        "data": {
            "valid": True,
            "user_id": current_user["id"],
            "username": current_user["username"]
        }
    }