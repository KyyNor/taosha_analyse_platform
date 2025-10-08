"""
系统相关 Schemas
"""
from pydantic import Field
from typing import Optional, List
from datetime import datetime
from .base import BaseSchema, BaseCreateSchema, BaseUpdateSchema, BaseResponseSchema


class UserCreate(BaseCreateSchema):
    """用户创建 Schema"""
    username: str = Field(description="用户名")
    email: str = Field(description="邮箱")
    password: str = Field(description="密码")
    full_name: Optional[str] = Field(default=None, description="姓名")
    role_id: Optional[int] = Field(default=None, description="角色ID")


class UserUpdate(BaseUpdateSchema):
    """用户更新 Schema"""
    email: Optional[str] = Field(default=None, description="邮箱")
    full_name: Optional[str] = Field(default=None, description="姓名")
    is_active: Optional[bool] = Field(default=None, description="是否激活")
    role_id: Optional[int] = Field(default=None, description="角色ID")


class UserResponse(BaseResponseSchema):
    """用户响应 Schema"""
    username: str = Field(description="用户名")
    email: str = Field(description="邮箱")
    full_name: Optional[str] = Field(description="姓名")
    is_active: bool = Field(description="是否激活")
    role_id: Optional[int] = Field(description="角色ID")
    role_name: Optional[str] = Field(description="角色名称")


class RoleCreate(BaseCreateSchema):
    """角色创建 Schema"""
    name: str = Field(description="角色名称")
    description: Optional[str] = Field(default=None, description="角色描述")
    permissions: Optional[List[int]] = Field(default=None, description="权限ID列表")


class RoleResponse(BaseResponseSchema):
    """角色响应 Schema"""
    name: str = Field(description="角色名称")
    description: Optional[str] = Field(description="角色描述")
    permissions: Optional[List["PermissionResponse"]] = Field(description="权限列表")


class PermissionResponse(BaseResponseSchema):
    """权限响应 Schema"""
    name: str = Field(description="权限名称")
    code: str = Field(description="权限代码")
    description: Optional[str] = Field(description="权限描述")
    module: str = Field(description="所属模块")