"""
简化的权限认证模块
用于快速启动应用
"""
from typing import Optional, Dict, Any


class SimplePermissionChecker:
    """简化的权限检查器"""
    
    def __init__(self):
        pass
    
    def create_access_token(self, data: dict) -> str:
        """创建访问令牌"""
        # 简化版本，直接返回测试token
        return "test_token_123"
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """验证token"""
        # 简化版本，直接返回测试用户信息
        return {
            "sub": 1,
            "username": "admin"
        }


# 全局权限检查器实例
permission_checker = SimplePermissionChecker()


async def get_current_user() -> Dict[str, Any]:
    """获取当前认证用户"""
    # 简化版本，直接返回测试用户
    return {
        "id": 1,
        "username": "admin", 
        "email": "admin@example.com",
        "full_name": "管理员",
        "is_active": True,
        "is_superuser": True,
        "roles": [{"id": 1, "name": "admin", "description": "管理员"}],
        "permissions": ["*"]
    }


async def get_optional_current_user() -> Optional[Dict[str, Any]]:
    """获取当前用户（可选）"""
    return await get_current_user()


def require_permissions(*required_permissions: str):
    """权限装饰器工厂"""
    def permission_dependency() -> dict:
        # 简化版本，直接返回管理员用户
        return {
            "id": 1,
            "username": "admin",
            "is_superuser": True,
            "permissions": ["*"]
        }
    return permission_dependency


def require_roles(*required_roles: str):
    """角色装饰器工厂"""
    def role_dependency() -> dict:
        # 简化版本，直接返回管理员用户
        return {
            "id": 1,
            "username": "admin",
            "is_superuser": True,
            "roles": [{"name": "admin"}]
        }
    return role_dependency


def require_superuser():
    """超级用户装饰器"""
    def superuser_dependency() -> dict:
        # 简化版本，直接返回管理员用户
        return {
            "id": 1,
            "username": "admin",
            "is_superuser": True
        }
    return superuser_dependency


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