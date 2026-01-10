"""
认证中间件
提供FastAPI依赖注入函数用于用户认证和权限验证
"""

from typing import Optional
from fastapi import Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
from cachetools import TTLCache
import threading
import hashlib

from models.db_base import get_db_session
from services.token_service import get_token_service, UserInfo
from services.permission_service import PermissionService, LoginRecordService
from utils.logger import logger

# 用于记录已处理的 token，避免重复记录登录
_recorded_tokens = TTLCache(maxsize=1000, ttl=43200)  # 缓存12小时
_record_lock = threading.Lock()


async def get_current_user(
    authorization: Optional[str] = Header(None, alias="Authorization")
) -> UserInfo:
    """
    获取当前用户信息的依赖注入函数
    
    Args:
        authorization: Authorization header，格式为 "Bearer <token>"
        
    Returns:
        UserInfo: 当前用户信息
        
    Raises:
        HTTPException: 401 - token缺失、无效或过期
    """
    if not authorization:
        logger.warning("请求缺少Authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not authorization.startswith("Bearer "):
        logger.warning(f"Authorization header格式错误: {authorization[:20]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = authorization.split(" ")[1]
    
    try:
        # 解析token
        token_service = get_token_service()
        user_info = token_service.decode_token(token)
        
        # 验证token
        if not token_service.validate_token(user_info):
            logger.warning(f"Token验证失败，用户: {user_info.user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 记录登录信息（同一个token只记录一次）
        token_hash = hashlib.sha256(token.encode()).hexdigest()[:16]  # 避免存储完整token
        
        with _record_lock:
            if token_hash not in _recorded_tokens:
                _recorded_tokens[token_hash] = True
                
                # 异步记录登录（不影响主流程）
                try:
                    with get_db_session() as db:
                        login_service = LoginRecordService(db)
                        login_service.record_login(
                            user_id=user_info.user_id,
                            user_name=user_info.user_name,
                            branch_no=user_info.branch_no,
                            branch_name=user_info.branch_name,
                            role_id_list=user_info.role_id_list
                        )
                        logger.info(f"首次记录用户登录: {user_info.user_id}")
                except Exception as e:
                    # 登录记录失败不应该影响主流程
                    logger.error(f"记录登录信息失败: {e}")
            else:
                logger.debug(f"Token已记录过登录，跳过: {user_info.user_id}")
        
        logger.debug(f"用户认证成功: {user_info.user_id}")
        return user_info
        
    except ValueError as e:
        logger.warning(f"Token解析失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"用户认证过程中发生错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def require_admin_role(
    current_user: UserInfo = Depends(get_current_user)
) -> UserInfo:
    """
    要求管理员角色的依赖注入函数
    
    Args:
        current_user: 当前用户信息
        
    Returns:
        UserInfo: 当前用户信息（已验证为管理员）
        
    Raises:
        HTTPException: 403 - 用户不是管理员
    """
    try:
        with get_db_session() as db:
            permission_service = PermissionService(db)

            if not permission_service.is_admin_user(current_user.branch_no, current_user.role_id_list):
                logger.warning(f"用户 {current_user.user_id} 尝试访问管理员功能，但不是管理员")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admin role required"
                )
        
        logger.debug(f"管理员权限验证通过: {current_user.user_id}")
        return current_user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"管理员权限验证过程中发生错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Permission check failed"
        )


async def check_page_permission(
    page_path: str,
    current_user: UserInfo = Depends(get_current_user)
) -> UserInfo:
    """
    检查页面访问权限的依赖注入函数
    
    Args:
        page_path: 页面路径
        current_user: 当前用户信息
        
    Returns:
        UserInfo: 当前用户信息（已验证有权限）
        
    Raises:
        HTTPException: 403 - 用户没有访问权限
    """
    try:
        with get_db_session() as db:
            permission_service = PermissionService(db)
            
            if not permission_service.check_page_access(
                current_user.branch_no, 
                current_user.role_id_list, 
                page_path
            ):
                logger.warning(f"用户 {current_user.user_id} 尝试访问页面 {page_path}，但没有权限")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"No permission to access {page_path}"
                )
        
        logger.debug(f"页面权限验证通过: 用户={current_user.user_id}, 页面={page_path}")
        return current_user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"页面权限验证过程中发生错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Permission check failed"
        )


def create_page_permission_dependency(page_path: str):
    """
    创建特定页面权限检查的依赖注入函数工厂
    
    Args:
        page_path: 页面路径
        
    Returns:
        依赖注入函数
        
    Usage:
        require_dashboard_access = create_page_permission_dependency("/dashboard")
        
        @router.get("/dashboard")
        async def dashboard(user: UserInfo = Depends(require_dashboard_access)):
            pass
    """
    async def page_permission_dependency(
        current_user: UserInfo = Depends(get_current_user)
    ) -> UserInfo:
        return await check_page_permission(page_path, current_user)
    
    return page_permission_dependency


# 常用的权限依赖
require_dashboard_access = create_page_permission_dependency("/dashboard")
require_admin_management_access = create_page_permission_dependency("/admin")