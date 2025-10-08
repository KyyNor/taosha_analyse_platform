"""
用户管理服务
处理用户、角色、权限的业务逻辑
"""
import secrets
import string
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from passlib.context import CryptContext

from db.database import get_async_db
from models.user_models import User, Role, Permission, UserRole, RolePermission
from schemas.user_schemas import (
    UserCreate, UserUpdate, UserResponse, UserWithRoles,
    RoleCreate, RoleUpdate, RoleResponse, RoleWithPermissions,
    PermissionCreate, PermissionResponse, UserFilter
)
from utils.logger import get_logger
from utils.exceptions import BusinessException

logger = get_logger(__name__)

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserService:
    """用户管理服务类"""
    
    def __init__(self):
        self.db_dependency = get_async_db
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """生成密码哈希"""
        return pwd_context.hash(password)
    
    def generate_random_password(self, length: int = 12) -> str:
        """生成随机密码"""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        return password
    
    async def create_user(
        self, 
        user_data: UserCreate,
        db: AsyncSession = None
    ) -> UserResponse:
        """创建用户"""
        try:
            if not db:
                async for session in self.db_dependency():
                    db = session
                    break
            
            # 创建用户
            hashed_password = self.get_password_hash(user_data.password)
            
            user = User(
                username=user_data.username,
                email=user_data.email,
                full_name=user_data.full_name,
                hashed_password=hashed_password,
                is_active=user_data.is_active,
                is_superuser=user_data.is_superuser
            )
            
            db.add(user)
            await db.flush()  # 获取用户ID
            
            # 分配角色
            if user_data.role_ids:
                await self._assign_user_roles_internal(user.id, user_data.role_ids, db)
            
            await db.commit()
            await db.refresh(user)
            
            logger.info(f"创建用户成功: {user.username}")
            return UserResponse.from_orm(user)
            
        except Exception as e:
            await db.rollback()
            logger.error(f"创建用户失败: {e}", exc_info=True)
            raise BusinessException(f"创建用户失败: {e}")
    
    async def get_user_by_id(
        self,
        user_id: int,
        db: AsyncSession = None
    ) -> Optional[User]:
        """根据ID获取用户"""
        try:
            if not db:
                async for session in self.db_dependency():
                    db = session
                    break
            
            stmt = select(User).where(User.id == user_id)
            result = await db.execute(stmt)
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"获取用户失败: {e}", exc_info=True)
            raise BusinessException(f"获取用户失败: {e}")
    
    async def get_user_by_username(
        self,
        username: str,
        db: AsyncSession = None
    ) -> Optional[User]:
        """根据用户名获取用户"""
        try:
            if not db:
                async for session in self.db_dependency():
                    db = session
                    break
            
            stmt = select(User).where(User.username == username)
            result = await db.execute(stmt)
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"获取用户失败: {e}", exc_info=True)
            raise BusinessException(f"获取用户失败: {e}")
    
    async def get_user_by_email(
        self,
        email: str,
        db: AsyncSession = None
    ) -> Optional[User]:
        """根据邮箱获取用户"""
        try:
            if not db:
                async for session in self.db_dependency():
                    db = session
                    break
            
            stmt = select(User).where(User.email == email)
            result = await db.execute(stmt)
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"获取用户失败: {e}", exc_info=True)
            raise BusinessException(f"获取用户失败: {e}")
    
    async def get_users(
        self,
        page: int = 1,
        page_size: int = 20,
        keyword: Optional[str] = None,
        is_active: Optional[bool] = None,
        db: AsyncSession = None
    ) -> Tuple[List[UserResponse], int]:
        """获取用户列表"""
        try:
            if not db:
                async for session in self.db_dependency():
                    db = session
                    break
            
            # 构建查询条件
            conditions = []
            
            if keyword:
                keyword_condition = or_(
                    User.username.ilike(f"%{keyword}%"),
                    User.full_name.ilike(f"%{keyword}%"),
                    User.email.ilike(f"%{keyword}%")
                )
                conditions.append(keyword_condition)
            
            if is_active is not None:
                conditions.append(User.is_active == is_active)
            
            # 查询总数
            count_stmt = select(func.count(User.id))
            if conditions:
                count_stmt = count_stmt.where(and_(*conditions))
            
            count_result = await db.execute(count_stmt)
            total_count = count_result.scalar()
            
            # 查询列表数据
            stmt = select(User)
            if conditions:
                stmt = stmt.where(and_(*conditions))
            
            stmt = (
                stmt.order_by(User.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            
            result = await db.execute(stmt)
            users = result.scalars().all()
            
            # 转换为响应模型
            user_responses = [UserResponse.from_orm(user) for user in users]
            
            return user_responses, total_count
            
        except Exception as e:
            logger.error(f"获取用户列表失败: {e}", exc_info=True)
            raise BusinessException(f"获取用户列表失败: {e}")
    
    async def get_user_with_roles(
        self,
        user_id: int,
        db: AsyncSession = None
    ) -> Optional[UserWithRoles]:
        """获取用户及其角色信息"""
        try:
            if not db:
                async for session in self.db_dependency():
                    db = session
                    break
            
            # 查询用户及其角色
            stmt = (
                select(User)
                .options(
                    selectinload(User.roles).selectinload(Role.permissions)
                )
                .where(User.id == user_id)
            )
            
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                return None
            
            # 收集权限
            permissions = set()
            roles = []
            
            for role in user.roles:
                roles.append(RoleResponse.from_orm(role))
                for permission in role.permissions:
                    permissions.add(permission.permission_code)
            
            # 构建响应
            user_response = UserWithRoles(
                **UserResponse.from_orm(user).dict(),
                roles=roles,
                permissions=list(permissions)
            )
            
            return user_response
            
        except Exception as e:
            logger.error(f"获取用户角色信息失败: {e}", exc_info=True)
            raise BusinessException(f"获取用户角色信息失败: {e}")
    
    async def update_user(
        self,
        user_id: int,
        user_data: UserUpdate,
        db: AsyncSession = None
    ) -> Optional[UserResponse]:
        """更新用户信息"""
        try:
            if not db:
                async for session in self.db_dependency():
                    db = session
                    break
            
            # 查找用户
            stmt = select(User).where(User.id == user_id)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                return None
            
            # 更新字段
            update_fields = user_data.model_dump(exclude_unset=True)
            for field, value in update_fields.items():
                if hasattr(user, field):
                    setattr(user, field, value)
            
            user.updated_at = datetime.now()
            
            await db.commit()
            await db.refresh(user)
            
            logger.info(f"更新用户成功: {user.username}")
            return UserResponse.from_orm(user)
            
        except Exception as e:
            await db.rollback()
            logger.error(f"更新用户失败: {e}", exc_info=True)
            raise BusinessException(f"更新用户失败: {e}")
    
    async def delete_user(
        self,
        user_id: int,
        db: AsyncSession = None
    ) -> bool:
        """删除用户（软删除）"""
        try:
            if not db:
                async for session in self.db_dependency():
                    db = session
                    break
            
            # 查找用户
            stmt = select(User).where(User.id == user_id)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                return False
            
            # 软删除：设置为非活跃状态
            user.is_active = False
            user.updated_at = datetime.now()
            
            await db.commit()
            
            logger.info(f"删除用户成功: {user.username}")
            return True
            
        except Exception as e:
            await db.rollback()
            logger.error(f"删除用户失败: {e}", exc_info=True)
            raise BusinessException(f"删除用户失败: {e}")
    
    async def reset_user_password(
        self,
        user_id: int,
        db: AsyncSession = None
    ) -> str:
        """重置用户密码"""
        try:
            if not db:
                async for session in self.db_dependency():
                    db = session
                    break
            
            # 查找用户
            stmt = select(User).where(User.id == user_id)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                raise BusinessException("用户不存在")
            
            # 生成新密码
            new_password = self.generate_random_password()
            user.hashed_password = self.get_password_hash(new_password)
            user.updated_at = datetime.now()
            
            await db.commit()
            
            logger.info(f"重置用户密码成功: {user.username}")
            return new_password
            
        except Exception as e:
            await db.rollback()
            logger.error(f"重置用户密码失败: {e}", exc_info=True)
            raise BusinessException(f"重置用户密码失败: {e}")
    
    async def change_user_password(
        self,
        user_id: int,
        old_password: str,
        new_password: str,
        db: AsyncSession = None
    ) -> bool:
        """修改用户密码"""
        try:
            if not db:
                async for session in self.db_dependency():
                    db = session
                    break
            
            # 查找用户
            stmt = select(User).where(User.id == user_id)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                return False
            
            # 验证旧密码
            if not self.verify_password(old_password, user.hashed_password):
                return False
            
            # 更新密码
            user.hashed_password = self.get_password_hash(new_password)
            user.updated_at = datetime.now()
            
            await db.commit()
            
            logger.info(f"修改用户密码成功: {user.username}")
            return True
            
        except Exception as e:
            await db.rollback()
            logger.error(f"修改用户密码失败: {e}", exc_info=True)
            raise BusinessException(f"修改用户密码失败: {e}")
    
    async def toggle_user_status(
        self,
        user_id: int,
        db: AsyncSession = None
    ) -> Optional[User]:
        """切换用户状态"""
        try:
            if not db:
                async for session in self.db_dependency():
                    db = session
                    break
            
            # 查找用户
            stmt = select(User).where(User.id == user_id)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                return None
            
            # 切换状态
            user.is_active = not user.is_active
            user.updated_at = datetime.now()
            
            await db.commit()
            await db.refresh(user)
            
            status_text = "启用" if user.is_active else "禁用"
            logger.info(f"{status_text}用户成功: {user.username}")
            
            return user
            
        except Exception as e:
            await db.rollback()
            logger.error(f"切换用户状态失败: {e}", exc_info=True)
            raise BusinessException(f"切换用户状态失败: {e}")
    
    async def assign_user_roles(
        self,
        user_id: int,
        role_ids: List[int],
        db: AsyncSession = None
    ) -> Optional[UserWithRoles]:
        """分配用户角色"""
        try:
            if not db:
                async for session in self.db_dependency():
                    db = session
                    break
            
            # 检查用户是否存在
            user = await self.get_user_by_id(user_id, db)
            if not user:
                return None
            
            await self._assign_user_roles_internal(user_id, role_ids, db)
            await db.commit()
            
            # 返回更新后的用户信息
            return await self.get_user_with_roles(user_id, db)
            
        except Exception as e:
            await db.rollback()
            logger.error(f"分配用户角色失败: {e}", exc_info=True)
            raise BusinessException(f"分配用户角色失败: {e}")
    
    async def _assign_user_roles_internal(
        self,
        user_id: int,
        role_ids: List[int],
        db: AsyncSession
    ):
        """内部方法：分配用户角色"""
        # 删除现有角色关联
        delete_stmt = select(UserRole).where(UserRole.user_id == user_id)
        result = await db.execute(delete_stmt)
        existing_roles = result.scalars().all()
        
        for role_relation in existing_roles:
            await db.delete(role_relation)
        
        # 添加新的角色关联
        for role_id in role_ids:
            user_role = UserRole(user_id=user_id, role_id=role_id)
            db.add(user_role)
    
    async def authenticate_user(
        self,
        username: str,
        password: str,
        db: AsyncSession = None
    ) -> Optional[User]:
        """用户认证"""
        try:
            if not db:
                async for session in self.db_dependency():
                    db = session
                    break
            
            # 支持用户名或邮箱登录
            stmt = select(User).where(
                or_(User.username == username, User.email == username)
            )
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                return None
            
            if not user.is_active:
                return None
            
            if not self.verify_password(password, user.hashed_password):
                return None
            
            # 更新最后登录时间
            user.last_login_at = datetime.now()
            await db.commit()
            
            return user
            
        except Exception as e:
            logger.error(f"用户认证失败: {e}", exc_info=True)
            return None