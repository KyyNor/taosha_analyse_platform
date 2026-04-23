"""
权限管理服务层
"""

from typing import List, Set, Dict, Optional
from sqlalchemy.orm import Session
from datetime import datetime
import uuid

from models.permission_models import SystemEntity, EntityType, SystemPage, SystemLoginRecord, SystemPermission
from repositories.permission_repository import PermissionRepository
from utils.logger import logger


class PermissionService:
    """权限管理服务"""

    def __init__(self, db: Session):
        self.db = db
        self.repo = PermissionRepository(db)

    def get_user_permissions(self, branch_no: str, role_id_list: List[str]) -> Set[str]:
        """获取用户的页面权限集合（部门权限 + 角色权限的并集）"""
        # 获取部门实体
        dept_entity = self.repo.get_entity_by_code_and_type(branch_no, EntityType.DEPARTMENT)
        dept_entity_ids = [dept_entity.id] if dept_entity else []

        # 获取角色实体
        role_entities = self.repo.get_entities_by_codes(role_id_list, EntityType.ROLE)
        role_entity_ids = [entity.id for entity in role_entities]

        # 合并实体ID列表
        all_entity_ids = dept_entity_ids + role_entity_ids

        if not all_entity_ids:
            return set()

        # 获取所有权限对应的页面路径
        page_paths = self.repo.get_page_paths_by_entity_ids(all_entity_ids)

        logger.debug(f"用户权限计算: 部门={branch_no}, 角色={role_id_list}, 权限页面数={len(page_paths)}")
        return page_paths

    def _match_page_permission(self, permitted_path: str, actual_path: str) -> bool:
        """
        匹配页面权限路径（支持动态路由模式）

        Args:
            permitted_path: 用户有权限的路径（可能是模板，如 "/metadata/tables/[tableId]"）
            actual_path: 实际访问的路径（如 "/metadata/tables/123"）

        Returns:
            bool: 是否匹配

        Examples:
            >>> _match_page_permission("/metadata/tables/[tableId]", "/metadata/tables/123")
            True
            >>> _match_page_permission("/agent", "/agent")
            True
            >>> _match_page_permission("/metadata/tables/[tableId]", "/metadata/relations/123")
            False
        """
        # 1. 精确匹配（处理普通路径）
        if permitted_path == actual_path:
            return True

        # 2. 动态路由匹配（处理 [param] 模式）
        if "[" in permitted_path and "]" in permitted_path:
            import re

            # 将模板路径转换为正则表达式
            # "/metadata/tables/[tableId]" -> r"^/metadata/tables/[^/]+$"
            # "/metadata/tables/[id]/column/[colId]" -> r"^/metadata/tables/[^/]+/column/[^/]+$"
            parts = permitted_path.split("/")
            regex_parts = []

            for part in parts:
                if not part:  # 空字符串（连续斜杠或路径开头/结尾）
                    regex_parts.append("")
                elif part.startswith("[") and part.endswith("]"):
                    # 参数部分（如 [id]）
                    regex_parts.append("[^/]+")
                else:
                    # 静态部分（如 fraudhunter, indicator-tasks）
                    regex_parts.append(part)

            # 构建正则表达式
            regex_pattern = "^" + "/".join(regex_parts) + "$"


            # 匹配路径
            if re.match(regex_pattern, actual_path):
                return True

        return False

    def check_page_access(self, branch_no: str, role_id_list: List[str], page_path: str) -> bool:
        """检查用户是否有访问指定页面的权限（支持动态路由匹配）"""
        # 首先检查页面是否存在
        # if not self.repo.get_page_by_path(page_path):
        #     logger.info(f"页面访问检查: 页面={page_path}, 页面不存在")
        #     return False

        # 管理员有所有存在页面的访问权限
        if self.is_admin_user(branch_no, role_id_list):
            logger.debug(f"页面访问检查: 页面={page_path}, 管理员用户，允许访问")
            return True

        # 普通用户检查具体权限（支持动态路由匹配）
        user_permissions = self.get_user_permissions(branch_no, role_id_list)
        logger.debug(f"用户权限页面清单：{user_permissions}")

        # 遍历所有权限路径，使用模式匹配
        for permitted_path in user_permissions:
            if self._match_page_permission(permitted_path, page_path):
                logger.debug(f"页面访问检查: 页面={page_path}, 匹配到权限模板 {permitted_path}")
                return True

        logger.warning(f"页面访问检查: 页面={page_path}, 无权限")
        return False
    
    def is_admin_user(self, branch_no: str, role_id_list: List[str]) -> bool:
        """检查用户是否为管理员"""
        # 检查部门是否为管理员
        dept_entity = self.repo.get_entity_by_code_and_type(branch_no, EntityType.DEPARTMENT)
        if dept_entity and dept_entity.is_admin:
            logger.debug(f"用户所属部门 {branch_no} 为管理员部门")
            return True

        # 检查角色是否有管理员角色
        role_entities = self.repo.get_entities_by_codes(role_id_list, EntityType.ROLE)
        for role in role_entities:
            if role.is_admin:
                logger.debug(f"用户拥有管理员角色: {role.code}")
                return True

        return False


class EntityService:
    """实体管理服务（部门和角色）"""
    
    def __init__(self, db: Session):
        self.db = db
        self.repo = PermissionRepository(db)
    
    def create_entity(self, code: str, name: str, entity_type: EntityType, description: str = None, is_admin: bool = False) -> SystemEntity:
        """创建实体"""
        try:
            # 检查编码是否已存在
            existing = self.repo.get_entity_by_code_and_type(code, entity_type)
            if existing:
                raise ValueError(f"{entity_type.value}编码 '{code}' 已存在")

            entity = SystemEntity(
                id=str(uuid.uuid4()),
                code=code,
                name=name,
                type=entity_type,
                description=description,
                is_admin=is_admin
            )
            
            return self.repo.create_entity(entity)
            
        except Exception as e:
            logger.error(f"创建{entity_type.value}失败: {e}")
            raise
    
    def update_entity(self, entity_id: str, name: str = None, description: str = None, is_admin: bool = None) -> SystemEntity:
        """更新实体"""
        try:
            entity = self.repo.get_entity_by_id(entity_id)
            if not entity:
                raise ValueError(f"实体 {entity_id} 不存在")

            if name is not None:
                entity.name = name
            if description is not None:
                entity.description = description
            if is_admin is not None:
                entity.is_admin = is_admin
            
            return self.repo.update_entity(entity)
            
        except Exception as e:
            logger.error(f"更新实体失败: {e}")
            raise
    
    def delete_entity(self, entity_id: str) -> bool:
        """删除实体"""
        try:
            # 先删除相关权限
            self.repo.delete_permissions_by_entity_id(entity_id)
            
            # 再删除实体
            return self.repo.delete_entity(entity_id)
            
        except Exception as e:
            logger.error(f"删除实体失败: {e}")
            raise
    
    def get_entities_by_type(self, entity_type: EntityType) -> List[SystemEntity]:
        """根据类型获取实体列表"""
        return self.repo.get_entities_by_type(entity_type)
    
    def assign_page_permissions(self, entity_id: str, page_ids: List[str]) -> bool:
        """为实体分配页面权限"""
        try:
            # 先删除现有权限
            self.repo.delete_permissions_by_entity_id(entity_id)
            
            # 创建新权限
            for page_id in page_ids:
                permission = SystemPermission(
                    id=str(uuid.uuid4()),
                    entity_id=entity_id,
                    page_id=page_id
                )
                self.repo.create_permission(permission)
            
            logger.info(f"为实体 {entity_id} 分配了 {len(page_ids)} 个页面权限")
            return True
            
        except Exception as e:
            logger.error(f"分配页面权限失败: {e}")
            raise


class PageService:
    """页面管理服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.repo = PermissionRepository(db)
    
    def create_page(self, path: str, name: str, description: str = None) -> SystemPage:
        """创建页面"""
        try:
            # 检查路径是否已存在
            existing = self.repo.get_page_by_path(path)
            if existing:
                raise ValueError(f"页面路径 '{path}' 已存在")
            
            page = SystemPage(
                id=str(uuid.uuid4()),
                path=path,
                name=name,
                description=description
            )
            
            return self.repo.create_page(page)
            
        except Exception as e:
            logger.error(f"创建页面失败: {e}")
            raise
    
    def get_all_pages(self) -> List[SystemPage]:
        """获取所有页面"""
        return self.repo.get_all_pages()
    
    def sync_pages_from_config(self, pages_config: List[Dict[str, str]]) -> int:
        """从配置同步页面信息"""
        try:
            synced_count = 0
            
            for page_data in pages_config:
                path = page_data.get("path")
                name = page_data.get("name")
                description = page_data.get("description", "")
                
                if not path or not name:
                    continue
                
                # 检查页面是否已存在
                existing = self.repo.get_page_by_path(path)
                if not existing:
                    # 创建新页面
                    self.create_page(path, name, description)
                    synced_count += 1
                else:
                    # 更新现有页面信息
                    existing.name = name
                    existing.description = description
                    self.repo.update_page(existing)
            
            logger.info(f"从配置同步了 {synced_count} 个页面")
            return synced_count
            
        except Exception as e:
            logger.error(f"同步页面配置失败: {e}")
            raise


class LoginRecordService:
    """登录记录服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.repo = PermissionRepository(db)
    
    def record_login(self, user_id: str, user_name: str, branch_no: str, branch_name: str, role_id_list: List[str]) -> SystemLoginRecord:
        """记录用户登录信息"""
        try:
            # 查询角色实体，获取角色名称列表（只包含在entity中存在的角色）
            role_entities = self.repo.get_entities_by_codes(role_id_list, EntityType.ROLE)
            role_name_list = [entity.name for entity in role_entities]
            
            record = SystemLoginRecord(
                user_id=user_id,
                user_name=user_name,
                branch_no=branch_no,
                branch_name=branch_name,
                role_id_list=role_id_list,
                role_name_list=role_name_list,
                last_login_time=datetime.now()
            )
            
            return self.repo.create_or_update_login_record(record)
            
        except Exception as e:
            logger.error(f"记录用户登录失败: {e}")
            raise
    
    def get_all_login_records(self) -> List[SystemLoginRecord]:
        """获取所有用户登录记录"""
        return self.repo.get_all_login_records()
    
    def get_last_login(self, user_id: str) -> Optional[SystemLoginRecord]:
        """获取用户最后登录记录"""
        return self.repo.get_login_record_by_user_id(user_id)