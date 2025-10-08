"""
简化的认证相关API
"""
from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any

from utils.logger import get_logger
from utils.simple_permissions import permission_checker, get_current_user

logger = get_logger(__name__)
router = APIRouter()


@router.post("/login")
async def login(username: str = None, password: str = None):
    """用户登录"""
    try:
        # 简化版本的登录验证
        if username in ["admin", "user"] and password in ["admin123", "user123"]:
            # 生成访问令牌
            access_token = permission_checker.create_access_token(
                data={"sub": 1, "username": username}
            )
            
            # 返回用户信息
            user_info = {
                "id": 1,
                "username": username,
                "email": f"{username}@example.com",
                "full_name": "测试用户" if username == "user" else "管理员",
                "is_active": True,
                "role_name": "user" if username == "user" else "admin"
            }
            
            return {
                "code": 0,
                "message": "登录成功",
                "data": {
                    "access_token": access_token,
                    "token_type": "bearer",
                    "expires_in": 3600,
                    "user": user_info
                }
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"用户登录失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登录失败"
        )


@router.post("/logout")
async def logout():
    """用户登出"""
    try:
        return {
            "code": 0,
            "message": "登出成功",
            "data": None
        }
        
    except Exception as e:
        logger.error(f"用户登出失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登出失败"
        )


@router.get("/me")
async def get_current_user_info():
    """获取当前用户信息"""
    try:
        user_info = await get_current_user()
        
        return {
            "code": 0,
            "message": "获取成功",
            "data": user_info
        }
        
    except Exception as e:
        logger.error(f"获取当前用户信息失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户信息失败"
        )


@router.post("/refresh-token")
async def refresh_token():
    """刷新访问令牌"""
    try:
        # 生成新的访问令牌
        access_token = permission_checker.create_access_token(
            data={"sub": 1, "username": "admin"}
        )
        
        return {
            "code": 0,
            "message": "刷新成功",
            "data": {
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": 3600
            }
        }
        
    except Exception as e:
        logger.error(f"刷新令牌失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="刷新令牌失败"
        )


@router.get("/check-token")
async def check_token():
    """检查令牌有效性"""
    return {
        "code": 0,
        "message": "Token有效",
        "data": {
            "valid": True,
            "user_id": 1,
            "username": "admin"
        }
    }