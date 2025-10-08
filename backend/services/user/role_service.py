"""
角色管理服务
处理角色和权限的业务逻辑
"""
from typing import List, Optional, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from db.database import get_async_db
from models.user_models import Role, Permission, RolePermission, UserRole
from schemas.user_schemas import (
    RoleCreate, RoleUpdate, RoleResponse, RoleWithPermissions,
    PermissionCreate, PermissionResponse
)
from utils.logger import get_logger
from utils.exceptions import BusinessException

logger = get_logger(__name__)


class RoleService:
    """角色管理服务类"""
    
    def __init__(self):
        self.db_dependency = get_async_db
    
    async def create_role(
        self, 
        role_data: RoleCreate,
        db: AsyncSession = None
    ) -> RoleResponse:
        """创建角色"""
        try:
            if not db:
                async for session in self.db_dependency():
                    db = session
                    break
            
            # 创建角色
            role = Role(
                role_name=role_data.role_name,
                description=role_data.description
            )
            
            db.add(role)
            await db.flush()  # 获取角色ID
            
            # 分配权限
            if role_data.permission_ids:
                await self._assign_role_permissions_internal(
                    role.id, role_data.permission_ids, db
                )
            
            await db.commit()
            await db.refresh(role)
            
            logger.info(f"创建角色成功: {role.role_name}")
            return RoleResponse.from_orm(role)
            
        except Exception as e:
            await db.rollback()
            logger.error(f"创建角色失败: {e}", exc_info=True)
            raise BusinessException(f"创建角色失败: {e}")
    
    async def get_role_by_id(
        self,
        role_id: int,
        db: AsyncSession = None
    ) -> Optional[Role]:
        """根据ID获取角色"""
        try:
            if not db:
                async for session in self.db_dependency():
                    db = session
                    break
            
            stmt = select(Role).where(Role.id == role_id)
            result = await db.execute(stmt)
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"获取角色失败: {e}", exc_info=True)
            raise BusinessException(f"获取角色失败: {e}")
    
    async def get_role_by_name(
        self,
        role_name: str,
        db: AsyncSession = None
    ) -> Optional[Role]:
        """根据角色名获取角色"""
        try:
            if not db:
                async for session in self.db_dependency():
                    db = session
                    break
            
            stmt = select(Role).where(Role.role_name == role_name)
            result = await db.execute(stmt)
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"获取角色失败: {e}", exc_info=True)
            raise BusinessException(f"获取角色失败: {e}")
    
    async def get_roles(
        self,
        page: int = 1,
        page_size: int = 20,
        keyword: Optional[str] = None,
        db: AsyncSession = None
    ) -> Tuple[List[RoleResponse], int]:
        """获取角色列表"""
        try:
            if not db:
                async for session in self.db_dependency():
                    db = session
                    break
            
            # 构建查询条件
            conditions = []
            
            if keyword:
                keyword_condition = or_(
                    Role.role_name.ilike(f"%{keyword}%"),
                    Role.description.ilike(f"%{keyword}%")
                )
                conditions.append(keyword_condition)
            
            # 查询总数
            count_stmt = select(func.count(Role.id))
            if conditions:
                count_stmt = count_stmt.where(and_(*conditions))
            
            count_result = await db.execute(count_stmt)
            total_count = count_result.scalar()
            
            # 查询列表数据
            stmt = select(Role)
            if conditions:
                stmt = stmt.where(and_(*conditions))
            
            stmt = (
                stmt.order_by(Role.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            
            result = await db.execute(stmt)
            roles = result.scalars().all()
            
            # 转换为响应模型
            role_responses = [RoleResponse.from_orm(role) for role in roles]
            
            return role_responses, total_count
            
        except Exception as e:
            logger.error(f"获取角色列表失败: {e}", exc_info=True)
            raise BusinessException(f"获取角色列表失败: {e}")
    
    async def get_role_with_permissions(
        self,
        role_id: int,
        db: AsyncSession = None
    ) -> Optional[RoleWithPermissions]:
        """获取角色及其权限信息"""
        try:
            if not db:
                async for session in self.db_dependency():
                    db = session
                    break
            
            # 查询角色及其权限
            stmt = (
                select(Role)
                .options(selectinload(Role.permissions))
                .where(Role.id == role_id)
            )
            
            result = await db.execute(stmt)
            role = result.scalar_one_or_none()
            
            if not role:
                return None
            
            # 转换权限
            permissions = [
                PermissionResponse.from_orm(permission) 
                for permission in role.permissions
            ]
            
            # 构建响应
            role_response = RoleWithPermissions(
                **RoleResponse.from_orm(role).dict(),
                permissions=permissions
            )
            
            return role_response
            
        except Exception as e:
            logger.error(f"获取角色权限信息失败: {e}", exc_info=True)
            raise BusinessException(f"获取角色权限信息失败: {e}")
    
    async def update_role(
        self,
        role_id: int,
        role_data: RoleUpdate,
        db: AsyncSession = None
    ) -> Optional[RoleResponse]:
        """更新角色信息"""
        try:
            if not db:
                async for session in self.db_dependency():
                    db = session
                    break
            
            # 查找角色
            stmt = select(Role).where(Role.id == role_id)
            result = await db.execute(stmt)
            role = result.scalar_one_or_none()
            
            if not role:
                return None
            
            # 更新字段
            update_fields = role_data.model_dump(exclude_unset=True, exclude={'permission_ids'})
            for field, value in update_fields.items():
                if hasattr(role, field):
                    setattr(role, field, value)
            
            role.updated_at = datetime.now()
            
            # 更新权限
            if role_data.permission_ids is not None:
                await self._assign_role_permissions_internal(
                    role.id, role_data.permission_ids, db
                )
            
            await db.commit()
            await db.refresh(role)
            
            logger.info(f"更新角色成功: {role.role_name}")
            return RoleResponse.from_orm(role)
            
        except Exception as e:
            await db.rollback()
            logger.error(f"更新角色失败: {e}", exc_info=True)
            raise BusinessException(f"更新角色失败: {e}")
    
    async def delete_role(
        self,
        role_id: int,
        db: AsyncSession = None
    ) -> bool:
        """删除角色"""
        try:
            if not db:
                async for session in self.db_dependency():
                    db = session
                    break
            
            # 查找角色
            stmt = select(Role).where(Role.id == role_id)
            result = await db.execute(stmt)
            role = result.scalar_one_or_none()
            
            if not role:
                return False
            
            # 删除角色权限关联
            permission_stmt = select(RolePermission).where(RolePermission.role_id == role_id)
            permission_result = await db.execute(permission_stmt)
            permissions = permission_result.scalars().all()
            
            for permission_relation in permissions:
                await db.delete(permission_relation)
            
            # 删除角色
            await db.delete(role)
            await db.commit()
            
            logger.info(f"删除角色成功: {role.role_name}")
            return True
            
        except Exception as e:
            await db.rollback()
            logger.error(f"删除角色失败: {e}", exc_info=True)
            raise BusinessException(f"删除角色失败: {e}")
    
    async def get_role_users_count(
        self,
        role_id: int,
        db: AsyncSession = None
    ) -> int:
        """获取角色关联的用户数量"""
        try:
            if not db:
                async for session in self.db_dependency():
                    db = session
                    break
            
            stmt = select(func.count(UserRole.user_id)).where(UserRole.role_id == role_id)
            result = await db.execute(stmt)
            return result.scalar()
            
        except Exception as e:
            logger.error(f"获取角色用户数量失败: {e}", exc_info=True)
            raise BusinessException(f"获取角色用户数量失败: {e}")
    
    async def assign_role_permissions(
        self,
        role_id: int,
        permission_ids: List[int],
        db: AsyncSession = None
    ) -> Optional[RoleWithPermissions]:
        """分配角色权限"""
        try:
            if not db:
                async for session in self.db_dependency():
                    db = session
                    break
            
            # 检查角色是否存在
            role = await self.get_role_by_id(role_id, db)
            if not role:
                return None
            
            await self._assign_role_permissions_internal(role_id, permission_ids, db)
            await db.commit()
            
            # 返回更新后的角色信息
            return await self.get_role_with_permissions(role_id, db)
            
        except Exception as e:
            await db.rollback()
            logger.error(f"分配角色权限失败: {e}", exc_info=True)
            raise BusinessException(f"分配角色权限失败: {e}")
    
    async def _assign_role_permissions_internal(
        self,
        role_id: int,
        permission_ids: List[int],
        db: AsyncSession
    ):
        """内部方法：分配角色权限"""
        # 删除现有权限关联
        delete_stmt = select(RolePermission).where(RolePermission.role_id == role_id)
        result = await db.execute(delete_stmt)
        existing_permissions = result.scalars().all()
        
        for permission_relation in existing_permissions:
            await db.delete(permission_relation)
        
        # 添加新的权限关联
        for permission_id in permission_ids:
            role_permission = RolePermission(role_id=role_id, permission_id=permission_id)
            db.add(role_permission)
    
    async def get_all_permissions(
        self,
        db: AsyncSession = None
    ) -> List[PermissionResponse]:
        """获取所有权限"""
        try:
            if not db:
                async for session in self.db_dependency():
                    db = session
                    break
            
            stmt = select(Permission).order_by(Permission.resource_type, Permission.permission_code)
            result = await db.execute(stmt)
            permissions = result.scalars().all()
            
            return [PermissionResponse.from_orm(permission) for permission in permissions]
            
        except Exception as e:
            logger.error(f"获取权限列表失败: {e}", exc_info=True)
            raise BusinessException(f"获取权限列表失败: {e}")
    
    async def create_permission(
        self,
        permission_data: PermissionCreate,
        db: AsyncSession = None
    ) -> PermissionResponse:
        """创建权限"""
        try:
            if not db:
                async for session in self.db_dependency():
                    db = session
                    break
            
            permission = Permission(
                permission_code=permission_data.permission_code,
                permission_name=permission_data.permission_name,
                description=permission_data.description,
                resource_type=permission_data.resource_type
            )
            
            db.add(permission)
            await db.commit()
            await db.refresh(permission)
            
            logger.info(f"创建权限成功: {permission.permission_code}")
            return PermissionResponse.from_orm(permission)
            
        except Exception as e:
            await db.rollback()
            logger.error(f"创建权限失败: {e}", exc_info=True)
            raise BusinessException(f"创建权限失败: {e}")