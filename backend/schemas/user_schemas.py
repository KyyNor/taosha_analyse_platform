"""
用户相关的Pydantic模型
"""
from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


class UserBase(BaseModel):
    """用户基础模型"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="邮箱")
    full_name: Optional[str] = Field(None, max_length=100, description="姓名")


class UserCreate(UserBase):
    """创建用户请求模型"""
    password: str = Field(..., min_length=6, max_length=128, description="密码")
    is_active: bool = Field(True, description="是否激活")
    is_superuser: bool = Field(False, description="是否超级用户")
    role_ids: Optional[List[int]] = Field(None, description="角色ID列表")

    @validator('password')
    def validate_password(cls, v):
        """密码复杂度验证"""
        if len(v) < 6:
            raise ValueError('密码长度至少6位')
        if not any(c.isdigit() for c in v):
            raise ValueError('密码必须包含数字')
        if not any(c.isalpha() for c in v):
            raise ValueError('密码必须包含字母')
        return v


class UserUpdate(BaseModel):
    """更新用户请求模型"""
    email: Optional[EmailStr] = Field(None, description="邮箱")
    full_name: Optional[str] = Field(None, max_length=100, description="姓名")
    is_active: Optional[bool] = Field(None, description="是否激活")
    is_superuser: Optional[bool] = Field(None, description="是否超级用户")


class UserResponse(UserBase):
    """用户响应模型"""
    id: int = Field(..., description="用户ID")
    is_active: bool = Field(..., description="是否激活")
    is_superuser: bool = Field(..., description="是否超级用户")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    last_login_at: Optional[datetime] = Field(None, description="最后登录时间")

    class Config:
        from_attributes = True


class RoleBase(BaseModel):
    """角色基础模型"""
    role_name: str = Field(..., min_length=2, max_length=50, description="角色名称")
    description: Optional[str] = Field(None, max_length=200, description="角色描述")


class RoleCreate(RoleBase):
    """创建角色请求模型"""
    permission_ids: Optional[List[int]] = Field(None, description="权限ID列表")


class RoleUpdate(BaseModel):
    """更新角色请求模型"""
    role_name: Optional[str] = Field(None, min_length=2, max_length=50, description="角色名称")
    description: Optional[str] = Field(None, max_length=200, description="角色描述")
    permission_ids: Optional[List[int]] = Field(None, description="权限ID列表")


class RoleResponse(RoleBase):
    """角色响应模型"""
    id: int = Field(..., description="角色ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")

    class Config:
        from_attributes = True


class PermissionBase(BaseModel):
    """权限基础模型"""
    permission_code: str = Field(..., min_length=2, max_length=100, description="权限代码")
    permission_name: str = Field(..., min_length=2, max_length=100, description="权限名称")
    description: Optional[str] = Field(None, max_length=200, description="权限描述")
    resource_type: Optional[str] = Field(None, max_length=50, description="资源类型")


class PermissionCreate(PermissionBase):
    """创建权限请求模型"""
    pass


class PermissionUpdate(BaseModel):
    """更新权限请求模型"""
    permission_name: Optional[str] = Field(None, min_length=2, max_length=100, description="权限名称")
    description: Optional[str] = Field(None, max_length=200, description="权限描述")
    resource_type: Optional[str] = Field(None, max_length=50, description="资源类型")


class PermissionResponse(PermissionBase):
    """权限响应模型"""
    id: int = Field(..., description="权限ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")

    class Config:
        from_attributes = True


class RoleWithPermissions(RoleResponse):
    """带权限的角色模型"""
    permissions: List[PermissionResponse] = Field([], description="权限列表")


class UserWithRoles(UserResponse):
    """带角色的用户模型"""
    roles: List[RoleResponse] = Field([], description="角色列表")
    permissions: List[str] = Field([], description="权限代码列表")


class LoginRequest(BaseModel):
    """登录请求模型"""
    username: str = Field(..., description="用户名或邮箱")
    password: str = Field(..., description="密码")


class LoginResponse(BaseModel):
    """登录响应模型"""
    access_token: str = Field(..., description="访问令牌")
    token_type: str = Field("bearer", description="令牌类型")
    expires_in: int = Field(..., description="过期时间(秒)")
    user: UserWithRoles = Field(..., description="用户信息")


class ChangePasswordRequest(BaseModel):
    """修改密码请求模型"""
    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., min_length=6, description="新密码")
    confirm_password: str = Field(..., description="确认密码")

    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('两次输入的密码不一致')
        return v

    @validator('new_password')
    def validate_new_password(cls, v):
        """新密码复杂度验证"""
        if len(v) < 6:
            raise ValueError('密码长度至少6位')
        if not any(c.isdigit() for c in v):
            raise ValueError('密码必须包含数字')
        if not any(c.isalpha() for c in v):
            raise ValueError('密码必须包含字母')
        return v


class ResetPasswordRequest(BaseModel):
    """重置密码请求模型"""
    email: EmailStr = Field(..., description="邮箱")


class UserFilter(BaseModel):
    """用户筛选条件"""
    keyword: Optional[str] = Field(None, description="搜索关键词")
    is_active: Optional[bool] = Field(None, description="激活状态")
    role_id: Optional[int] = Field(None, description="角色ID")
    created_start: Optional[datetime] = Field(None, description="创建开始时间")
    created_end: Optional[datetime] = Field(None, description="创建结束时间")


class RoleFilter(BaseModel):
    """角色筛选条件"""
    keyword: Optional[str] = Field(None, description="搜索关键词")


class UserStatistics(BaseModel):
    """用户统计信息"""
    total_users: int = Field(..., description="总用户数")
    active_users: int = Field(..., description="活跃用户数")
    inactive_users: int = Field(..., description="非活跃用户数")
    superuser_count: int = Field(..., description="超级用户数")
    user_growth: List[dict] = Field(..., description="用户增长趋势")
    role_distribution: List[dict] = Field(..., description="角色分布")


class BatchUserOperation(BaseModel):
    """批量用户操作"""
    user_ids: List[int] = Field(..., description="用户ID列表")
    operation: str = Field(..., description="操作类型: activate, deactivate, delete")


class AssignRolesRequest(BaseModel):
    """分配角色请求模型"""
    role_ids: List[int] = Field(..., description="角色ID列表")


class UserActivityLog(BaseModel):
    """用户活动日志"""
    id: int = Field(..., description="日志ID")
    user_id: int = Field(..., description="用户ID")
    action: str = Field(..., description="操作类型")
    resource: Optional[str] = Field(None, description="操作资源")
    ip_address: Optional[str] = Field(None, description="IP地址")
    user_agent: Optional[str] = Field(None, description="用户代理")
    created_at: datetime = Field(..., description="创建时间")

    class Config:
        from_attributes = True