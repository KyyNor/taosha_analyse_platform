"""
层级化权限服务
支持层级化页面权限的分配和查询
"""

from typing import Dict, List, Set, Any, Optional
from sqlalchemy.orm import Session
from loguru import logger

from models.permission_models import SystemPage, SystemEntity, EntityType, SystemLoginRecord
from repositories.permission_repository import PermissionRepository
from services.permission_assignment_service import PermissionAssignmentService


class HierarchicalPermissionService:
    """层级化权限服务"""

    def __init__(self, db: Session):
        self.db = db
        self.repo = PermissionRepository(db)
        self.assignment_service = PermissionAssignmentService(db)

    def assign_with_descendants(
        self,
        entity_id: str,
        page_id: str,
        include_descendants: bool = True
    ) -> Dict[str, Any]:
        """
        分配权限，可选择是否包含子页面

        Args:
            entity_id: 实体ID
            page_id: 页面ID
            include_descendants: 是否包含所有子孙页面

        Returns:
            Dict: 分配结果
        """
        try:
            # 添加当前页面权限
            self.assignment_service.add_page_to_entity(entity_id, page_id)

            descendant_count = 0

            if include_descendants:
                # 递归添加所有子页面
                descendants = self._get_all_descendants(page_id)
                for descendant_id in descendants:
                    self.assignment_service.add_page_to_entity(entity_id, descendant_id)
                    descendant_count += 1

            self.db.commit()

            return {
                "success": True,
                "entity_id": entity_id,
                "page_id": page_id,
                "descendants_count": descendant_count,
                "message": f"成功分配权限，包含 {descendant_count} 个子页面"
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"分配层级化权限失败: {str(e)}")
            return {
                "success": False,
                "message": f"分配失败: {str(e)}"
            }

    def _get_all_descendants(self, page_id: str) -> Set[str]:
        """
        获取页面的所有子孙页面ID

        Args:
            page_id: 页面ID

        Returns:
            Set[str]: 子孙页面ID集合
        """
        descendants = set()

        def collect(pid: str):
            """递归收集子页面"""
            children = self.repo.get_pages_by_parent_id(pid)
            for child in children:
                descendants.add(child.id)
                collect(child.id)

        collect(page_id)
        return descendants

    def get_page_entities(self, page_id: str) -> Dict[str, Any]:
        """
        获取指定页面的所有有权限实体（部门+角色）

        Args:
            page_id: 页面ID

        Returns:
            Dict: 包含departments和roles的字典
        """
        try:
            # 获取页面的所有权限记录
            permissions = self.repo.get_permissions_by_page_id(page_id)

            departments = []
            roles = []

            for perm in permissions:
                entity = perm.entity
                entity_info = {
                    "id": entity.id,
                    "code": entity.code,
                    "name": entity.name,
                    "type": entity.type.value,
                    "is_admin": entity.is_admin,
                    "has_permission": True
                }

                if entity.type == EntityType.DEPARTMENT:
                    departments.append(entity_info)
                else:  # ROLE
                    roles.append(entity_info)

            return {
                "success": True,
                "page_id": page_id,
                "departments": departments,
                "roles": roles,
                "total_departments": len(departments),
                "total_roles": len(roles)
            }

        except Exception as e:
            logger.error(f"获取页面实体列表失败: {str(e)}")
            return {
                "success": False,
                "message": f"获取失败: {str(e)}",
                "departments": [],
                "roles": []
            }

    def get_user_effective_permissions(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户最终权限（带层级结构）

        Args:
            user_id: 用户ID

        Returns:
            Dict: 包含用户信息和层级化权限树
        """
        try:
            # 获取用户登录记录
            record = self.repo.get_login_record_by_user_id(user_id)
            if not record:
                return {
                    "success": False,
                    "message": f"用户 {user_id} 的登录记录不存在"
                }

            # 获取部门实体
            dept_entity = self.repo.get_entity_by_code_and_type(
                record.branch_no,
                EntityType.DEPARTMENT
            )

            # 获取角色实体
            role_entities = self.repo.get_entities_by_codes(
                record.role_id_list,
                EntityType.ROLE
            )

            # 收集所有实体ID
            all_entity_ids = []
            if dept_entity:
                all_entity_ids.append(dept_entity.id)
            all_entity_ids.extend([e.id for e in role_entities])

            if not all_entity_ids:
                return {
                    "success": True,
                    "user_id": user_id,
                    "user_name": record.user_name,
                    "branch_no": record.branch_no,
                    "branch_name": record.branch_name,
                    "role_id_list": record.role_id_list,
                    "role_name_list": record.role_name_list,
                    "effective_permissions": [],
                    "permissions_tree": [],
                    "total_permissions": 0,
                    "message": "用户没有关联任何部门或角色"
                }

            # 获取权限页面路径
            page_paths = self.repo.get_page_paths_by_entity_ids(all_entity_ids)

            # 获取所有页面并过滤有权限的页面
            all_pages = self.repo.get_all_pages()
            permitted_pages = [p for p in all_pages if p.path in page_paths]

            # 构建层级树
            permissions_tree = self._build_permissions_tree(permitted_pages)

            return {
                "success": True,
                "user_id": user_id,
                "user_name": record.user_name,
                "branch_no": record.branch_no,
                "branch_name": record.branch_name,
                "role_id_list": record.role_id_list,
                "role_name_list": record.role_name_list,
                "effective_permissions": [
                    {
                        "id": p.id,
                        "path": p.path,
                        "name": p.name,
                        "description": p.description,
                        "level": p.level
                    }
                    for p in permitted_pages
                ],
                "permissions_tree": permissions_tree,
                "total_permissions": len(permitted_pages),
                "message": f"用户拥有 {len(permitted_pages)} 个页面权限"
            }

        except Exception as e:
            logger.error(f"获取用户最终权限失败: {str(e)}")
            return {
                "success": False,
                "message": f"获取失败: {str(e)}"
            }

    def _build_permissions_tree(self, pages: List[SystemPage]) -> List[Dict[str, Any]]:
        """
        构建层级权限树

        Args:
            pages: 页面列表

        Returns:
            List[Dict]: 层级化的权限树
        """
        # 构建页面映射
        page_map = {p.id: p for p in pages}

        # 递归构建树
        def build_tree(parent_id: Optional[str] = None) -> List[Dict[str, Any]]:
            """递归构建树形结构"""
            children = [p for p in pages if p.parent_id == parent_id]
            return [
                {
                    "id": child.id,
                    "path": child.path,
                    "name": child.name,
                    "description": child.description,
                    "level": child.level,
                    "children": build_tree(child.id)
                }
                for child in children
            ]

        return build_tree(None)

    def get_page_tree(self) -> List[Dict[str, Any]]:
        """
        获取完整的页面树形结构

        Returns:
            List[Dict]: 页面树
        """
        try:
            pages = self.repo.get_all_pages()
            return self._build_permissions_tree(pages)

        except Exception as e:
            logger.error(f"获取页面树失败: {str(e)}")
            return []
