"""
权限认证和授权中间件
"""
import jwt
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from db.database import get_async_db
from models.user_models import User, Role, Permission
from config.settings import get_settings
from utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()
security = HTTPBearer()


class PermissionChecker:
    """权限检查器"""
    
    def __init__(self):
        self.secret_key = settings.SECRET_KEY
        self.algorithm = "HS256"
        self.access_token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        """创建访问令牌"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """验证token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            user_id: int = payload.get("sub")
            if user_id is None:
                raise HTTPException(status_code=401, detail="无效的认证凭据")
            
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="认证凭据已过期")
        except jwt.JWTError:
            raise HTTPException(status_code=401, detail="无效的认证凭据")
    
    async def get_user_with_permissions(
        self, 
        user_id: int, 
        db: AsyncSession
    ) -> Optional[Dict[str, Any]]:
        """获取用户及其权限信息"""
        try:
            # 查询用户及其角色和权限
            stmt = (
                select(User)
                .options(
                    selectinload(User.roles).selectinload(Role.permissions)
                )
                .where(User.id == user_id, User.is_active == True)
            )
            
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                return None
            
            # 收集所有权限
            permissions = set()
            roles = []
            
            for role in user.roles:
                roles.append({
                    "id": role.id,
                    "name": role.role_name,
                    "description": role.description
                })
                
                for permission in role.permissions:
                    permissions.add(permission.permission_code)
            
            # 如果是超级用户，拥有所有权限
            if user.is_superuser:
                permissions.add("*")  # 超级权限标识
            
            return {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "is_active": user.is_active,
                "is_superuser": user.is_superuser,
                "roles": roles,
                "permissions": list(permissions)
            }
            
        except Exception as e:
            logger.error(f"获取用户权限信息失败: {e}", exc_info=True)
            return None


# 全局权限检查器实例
permission_checker = PermissionChecker()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_async_db)
) -> Dict[str, Any]:
    """获取当前认证用户"""
    try:
        # 验证token
        payload = permission_checker.verify_token(credentials.credentials)
        user_id = payload.get("sub")
        
        # 获取用户信息
        user_info = await permission_checker.get_user_with_permissions(user_id, db)
        if not user_info:
            raise HTTPException(status_code=401, detail="用户不存在或已被禁用")
        
        return user_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取当前用户失败: {e}", exc_info=True)
        raise HTTPException(status_code=401, detail="认证失败")


async def get_optional_current_user(
    request: Request,
    db: AsyncSession = Depends(get_async_db)
) -> Optional[Dict[str, Any]]:
    """获取当前用户（可选，不强制认证）"""
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        
        token = auth_header.split(" ")[1]
        payload = permission_checker.verify_token(token)
        user_id = payload.get("sub")
        
        return await permission_checker.get_user_with_permissions(user_id, db)
        
    except Exception:
        return None


def require_permissions(*required_permissions: str):
    """权限装饰器工厂"""
    def permission_dependency(current_user: dict = Depends(get_current_user)) -> dict:
        """权限依赖检查"""
        if not current_user:
            raise HTTPException(status_code=401, detail="需要认证")
        
        # 超级用户拥有所有权限
        if current_user.get("is_superuser") or "*" in current_user.get("permissions", []):
            return current_user
        
        # 检查具体权限
        user_permissions = set(current_user.get("permissions", []))
        
        for permission in required_permissions:
            # 支持通配符权限检查
            if permission not in user_permissions:
                # 检查是否有父级权限
                permission_parts = permission.split(":")
                for i in range(len(permission_parts) - 1, 0, -1):
                    parent_permission = ":".join(permission_parts[:i]) + ":*"
                    if parent_permission in user_permissions:
                        break
                else:
                    raise HTTPException(
                        status_code=403, 
                        detail=f"权限不足，需要权限: {permission}"
                    )
        
        return current_user
    
    return permission_dependency


def require_roles(*required_roles: str):
    """角色装饰器工厂"""
    def role_dependency(current_user: dict = Depends(get_current_user)) -> dict:
        """角色依赖检查"""
        if not current_user:
            raise HTTPException(status_code=401, detail="需要认证")
        
        # 超级用户拥有所有权限
        if current_user.get("is_superuser"):
            return current_user
        
        # 检查角色
        user_roles = {role["name"] for role in current_user.get("roles", [])}
        
        for role in required_roles:
            if role not in user_roles:
                raise HTTPException(
                    status_code=403, 
                    detail=f"权限不足，需要角色: {role}"
                )
        
        return current_user
    
    return role_dependency


def require_superuser():
    """超级用户装饰器"""
    def superuser_dependency(current_user: dict = Depends(get_current_user)) -> dict:
        """超级用户依赖检查"""
        if not current_user.get("is_superuser"):
            raise HTTPException(status_code=403, detail="需要超级用户权限")
        
        return current_user
    
    return superuser_dependency


class PermissionMiddleware:
    """权限中间件"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        """ASGI中间件接口"""
        if scope["type"] == "http":
            request = Request(scope, receive)
            
            # 获取路径和方法
            path = request.url.path
            method = request.method
            
            # 记录访问日志
            logger.info(f"API访问: {method} {path}")
            
            # 这里可以添加全局权限检查逻辑
            # 例如：API访问频率限制、IP白名单检查等
        
        await self.app(scope, receive, send)


# 权限常量定义
class Permissions:
    """权限常量"""
    
    # 系统权限
    SYSTEM_ADMIN = "system:admin"
    SYSTEM_READ = "system:read"
    SYSTEM_WRITE = "system:write"
    
    # 用户管理权限
    USER_READ = "user:read"
    USER_CREATE = "user:create"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    
    # 角色管理权限
    ROLE_READ = "role:read"
    ROLE_CREATE = "role:create"
    ROLE_UPDATE = "role:update"
    ROLE_DELETE = "role:delete"
    
    # 元数据管理权限
    METADATA_READ = "metadata:read"
    METADATA_CREATE = "metadata:create"
    METADATA_UPDATE = "metadata:update"
    METADATA_DELETE = "metadata:delete"
    
    # 查询权限
    QUERY_EXECUTE = "query:execute"
    QUERY_HISTORY = "query:history"
    QUERY_EXPORT = "query:export"
    
    # 数据主题权限
    THEME_READ = "theme:read"
    THEME_CREATE = "theme:create"
    THEME_UPDATE = "theme:update"
    THEME_DELETE = "theme:delete"


class Roles:
    """角色常量"""
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"