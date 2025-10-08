"""
初始化系统权限和角色数据
"""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.database import get_async_db
from models.user_models import Permission, Role, User, RolePermission, UserRole
from services.user.user_service import UserService
from services.user.role_service import RoleService
from utils.logger import get_logger
from utils.permissions import Permissions, Roles

logger = get_logger(__name__)


class InitPermissionData:
    """初始化权限数据类"""
    
    def __init__(self):
        self.db_dependency = get_async_db
    
    async def init_permissions(self, db: AsyncSession):
        """初始化系统权限"""
        permissions_data = [
            # 系统权限
            {"code": Permissions.SYSTEM_ADMIN, "name": "系统管理", "desc": "系统管理员权限", "type": "system"},
            {"code": Permissions.SYSTEM_READ, "name": "系统查看", "desc": "查看系统信息", "type": "system"},
            {"code": Permissions.SYSTEM_WRITE, "name": "系统配置", "desc": "修改系统配置", "type": "system"},
            
            # 用户管理权限
            {"code": Permissions.USER_READ, "name": "用户查看", "desc": "查看用户信息", "type": "user"},
            {"code": Permissions.USER_CREATE, "name": "用户创建", "desc": "创建新用户", "type": "user"},
            {"code": Permissions.USER_UPDATE, "name": "用户编辑", "desc": "编辑用户信息", "type": "user"},
            {"code": Permissions.USER_DELETE, "name": "用户删除", "desc": "删除用户", "type": "user"},
            
            # 角色管理权限
            {"code": Permissions.ROLE_READ, "name": "角色查看", "desc": "查看角色信息", "type": "role"},
            {"code": Permissions.ROLE_CREATE, "name": "角色创建", "desc": "创建新角色", "type": "role"},
            {"code": Permissions.ROLE_UPDATE, "name": "角色编辑", "desc": "编辑角色信息", "type": "role"},
            {"code": Permissions.ROLE_DELETE, "name": "角色删除", "desc": "删除角色", "type": "role"},
            
            # 元数据管理权限
            {"code": Permissions.METADATA_READ, "name": "元数据查看", "desc": "查看元数据信息", "type": "metadata"},
            {"code": Permissions.METADATA_CREATE, "name": "元数据创建", "desc": "创建元数据", "type": "metadata"},
            {"code": Permissions.METADATA_UPDATE, "name": "元数据编辑", "desc": "编辑元数据", "type": "metadata"},
            {"code": Permissions.METADATA_DELETE, "name": "元数据删除", "desc": "删除元数据", "type": "metadata"},
            
            # 查询权限
            {"code": Permissions.QUERY_EXECUTE, "name": "执行查询", "desc": "执行数据查询", "type": "query"},
            {"code": Permissions.QUERY_HISTORY, "name": "查询历史", "desc": "查看查询历史", "type": "query"},
            {"code": Permissions.QUERY_EXPORT, "name": "导出数据", "desc": "导出查询结果", "type": "query"},
            
            # 数据主题权限
            {"code": Permissions.THEME_READ, "name": "主题查看", "desc": "查看数据主题", "type": "theme"},
            {"code": Permissions.THEME_CREATE, "name": "主题创建", "desc": "创建数据主题", "type": "theme"},
            {"code": Permissions.THEME_UPDATE, "name": "主题编辑", "desc": "编辑数据主题", "type": "theme"},
            {"code": Permissions.THEME_DELETE, "name": "主题删除", "desc": "删除数据主题", "type": "theme"},
        ]
        
        created_permissions = []
        
        for perm_data in permissions_data:
            # 检查权限是否已存在
            stmt = select(Permission).where(Permission.permission_code == perm_data["code"])
            result = await db.execute(stmt)
            existing_permission = result.scalar_one_or_none()
            
            if not existing_permission:
                permission = Permission(
                    permission_code=perm_data["code"],
                    permission_name=perm_data["name"],
                    description=perm_data["desc"],
                    resource_type=perm_data["type"]
                )
                db.add(permission)
                created_permissions.append(perm_data["code"])
        
        await db.flush()
        logger.info(f"创建权限数量: {len(created_permissions)}")
        return created_permissions
    
    async def init_roles(self, db: AsyncSession):
        """初始化系统角色"""
        roles_data = [
            {
                "name": Roles.SUPER_ADMIN,
                "desc": "超级管理员，拥有所有权限",
                "permissions": [
                    Permissions.SYSTEM_ADMIN, Permissions.SYSTEM_READ, Permissions.SYSTEM_WRITE,
                    Permissions.USER_READ, Permissions.USER_CREATE, Permissions.USER_UPDATE, Permissions.USER_DELETE,
                    Permissions.ROLE_READ, Permissions.ROLE_CREATE, Permissions.ROLE_UPDATE, Permissions.ROLE_DELETE,
                    Permissions.METADATA_READ, Permissions.METADATA_CREATE, Permissions.METADATA_UPDATE, Permissions.METADATA_DELETE,
                    Permissions.QUERY_EXECUTE, Permissions.QUERY_HISTORY, Permissions.QUERY_EXPORT,
                    Permissions.THEME_READ, Permissions.THEME_CREATE, Permissions.THEME_UPDATE, Permissions.THEME_DELETE
                ]
            },
            {
                "name": Roles.ADMIN,
                "desc": "管理员，拥有大部分权限",
                "permissions": [
                    Permissions.SYSTEM_READ,
                    Permissions.USER_READ, Permissions.USER_CREATE, Permissions.USER_UPDATE,
                    Permissions.ROLE_READ,
                    Permissions.METADATA_READ, Permissions.METADATA_CREATE, Permissions.METADATA_UPDATE,
                    Permissions.QUERY_EXECUTE, Permissions.QUERY_HISTORY, Permissions.QUERY_EXPORT,
                    Permissions.THEME_READ, Permissions.THEME_CREATE, Permissions.THEME_UPDATE
                ]
            },
            {
                "name": Roles.ANALYST,
                "desc": "数据分析师，拥有查询和分析权限",
                "permissions": [
                    Permissions.METADATA_READ,
                    Permissions.QUERY_EXECUTE, Permissions.QUERY_HISTORY, Permissions.QUERY_EXPORT,
                    Permissions.THEME_READ
                ]
            },
            {
                "name": Roles.VIEWER,
                "desc": "查看者，只能查看数据",
                "permissions": [
                    Permissions.METADATA_READ,
                    Permissions.QUERY_EXECUTE, Permissions.QUERY_HISTORY,
                    Permissions.THEME_READ
                ]
            }
        ]
        
        created_roles = []
        
        for role_data in roles_data:
            # 检查角色是否已存在
            stmt = select(Role).where(Role.role_name == role_data["name"])
            result = await db.execute(stmt)
            existing_role = result.scalar_one_or_none()
            
            if not existing_role:
                # 创建角色
                role = Role(
                    role_name=role_data["name"],
                    description=role_data["desc"]
                )
                db.add(role)
                await db.flush()
                
                # 分配权限
                for permission_code in role_data["permissions"]:
                    # 查找权限
                    perm_stmt = select(Permission).where(Permission.permission_code == permission_code)
                    perm_result = await db.execute(perm_stmt)
                    permission = perm_result.scalar_one_or_none()
                    
                    if permission:
                        role_permission = RolePermission(role_id=role.id, permission_id=permission.id)
                        db.add(role_permission)
                
                created_roles.append(role_data["name"])
        
        await db.flush()
        logger.info(f"创建角色数量: {len(created_roles)}")
        return created_roles
    
    async def init_admin_user(self, db: AsyncSession):
        """初始化管理员用户"""
        try:
            # 检查是否已存在管理员用户
            stmt = select(User).where(User.username == "admin")
            result = await db.execute(stmt)
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                logger.info("管理员用户已存在")
                return existing_user
            
            # 创建管理员用户
            user_service = UserService()
            admin_password = "admin123456"  # 默认密码，生产环境应该修改
            
            admin_user = User(
                username="admin",
                email="admin@example.com",
                full_name="系统管理员",
                hashed_password=user_service.get_password_hash(admin_password),
                is_active=True,
                is_superuser=True
            )
            
            db.add(admin_user)
            await db.flush()
            
            # 分配超级管理员角色
            stmt = select(Role).where(Role.role_name == Roles.SUPER_ADMIN)
            result = await db.execute(stmt)
            admin_role = result.scalar_one_or_none()
            
            if admin_role:
                user_role = UserRole(user_id=admin_user.id, role_id=admin_role.id)
                db.add(user_role)
            
            await db.flush()
            
            logger.info(f"创建管理员用户成功: admin / {admin_password}")
            return admin_user
            
        except Exception as e:
            logger.error(f"创建管理员用户失败: {e}", exc_info=True)
            raise
    
    async def run_init(self):
        """运行初始化"""
        try:
            async for db in self.db_dependency():
                logger.info("开始初始化权限数据...")
                
                # 初始化权限
                await self.init_permissions(db)
                
                # 初始化角色
                await self.init_roles(db)
                
                # 初始化管理员用户
                await self.init_admin_user(db)
                
                # 提交事务
                await db.commit()
                
                logger.info("权限数据初始化完成")
                break
                
        except Exception as e:
            logger.error(f"初始化权限数据失败: {e}", exc_info=True)
            await db.rollback()
            raise


async def main():
    """主函数"""
    init_data = InitPermissionData()
    await init_data.run_init()


if __name__ == "__main__":
    asyncio.run(main())