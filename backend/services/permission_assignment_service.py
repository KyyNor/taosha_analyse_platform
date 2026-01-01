"""
权限分配服务
扩展EntityService，提供更完整的权限分配和管理功能
"""

from typing import List, Dict, Set, Optional
from sqlalchemy.orm import Session

from models.permission_models import SystemEntity, SystemPage, SystemPermission, EntityType
from repositories.permission_repository import PermissionRepository
from services.permission_service import EntityService
from utils.logger import logger
import uuid


class PermissionAssignmentService:
    """权限分配服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.repo = PermissionRepository(db)
        self.entity_service = EntityService(db)
    
    def assign_pages_to_entity(self, entity_id: str, page_ids: List[str]) -> bool:
        """
        为实体分配页面权限
        
        Args:
            entity_id: 实体ID
            page_ids: 页面ID列表
            
        Returns:
            bool: 是否分配成功
        """
        try:
            return self.entity_service.assign_page_permissions(entity_id, page_ids)
            
        except Exception as e:
            logger.error(f"为实体分配页面权限失败: {e}")
            raise
    
    def get_entity_permissions(self, entity_id: str) -> List[SystemPage]:
        """
        获取实体的权限页面列表
        
        Args:
            entity_id: 实体ID
            
        Returns:
            List[SystemPage]: 有权限的页面列表
        """
        try:
            permissions = self.repo.get_permissions_by_entity_id(entity_id)
            pages = []
            
            for permission in permissions:
                page = self.repo.get_page_by_id(permission.page_id)
                if page:
                    pages.append(page)
            
            return pages
            
        except Exception as e:
            logger.error(f"获取实体权限失败: {e}")
            return []
    
    def get_entity_permission_ids(self, entity_id: str) -> Set[str]:
        """
        获取实体的权限页面ID集合
        
        Args:
            entity_id: 实体ID
            
        Returns:
            Set[str]: 页面ID集合
        """
        try:
            permissions = self.repo.get_permissions_by_entity_id(entity_id)
            return {permission.page_id for permission in permissions}
            
        except Exception as e:
            logger.error(f"获取实体权限ID失败: {e}")
            return set()
    
    def add_page_to_entity(self, entity_id: str, page_id: str) -> bool:
        """
        为实体添加单个页面权限
        
        Args:
            entity_id: 实体ID
            page_id: 页面ID
            
        Returns:
            bool: 是否添加成功
        """
        try:
            # 检查权限是否已存在
            existing_permissions = self.get_entity_permission_ids(entity_id)
            if page_id in existing_permissions:
                logger.warning(f"实体 {entity_id} 已有页面 {page_id} 的权限")
                return True
            
            # 创建新权限
            permission = SystemPermission(
                id=str(uuid.uuid4()),
                entity_id=entity_id,
                page_id=page_id
            )
            
            self.repo.create_permission(permission)
            logger.info(f"为实体 {entity_id} 添加了页面 {page_id} 的权限")
            return True
            
        except Exception as e:
            logger.error(f"添加页面权限失败: {e}")
            raise
    
    def remove_page_from_entity(self, entity_id: str, page_id: str) -> bool:
        """
        移除实体的单个页面权限
        
        Args:
            entity_id: 实体ID
            page_id: 页面ID
            
        Returns:
            bool: 是否移除成功
        """
        try:
            success = self.repo.delete_permission(entity_id, page_id)
            if success:
                logger.info(f"移除了实体 {entity_id} 对页面 {page_id} 的权限")
            else:
                logger.warning(f"实体 {entity_id} 没有页面 {page_id} 的权限")
            
            return success
            
        except Exception as e:
            logger.error(f"移除页面权限失败: {e}")
            raise
    
    def get_page_entities(self, page_id: str) -> List[SystemEntity]:
        """
        获取有权限访问指定页面的所有实体
        
        Args:
            page_id: 页面ID
            
        Returns:
            List[SystemEntity]: 实体列表
        """
        try:
            # 查询所有有该页面权限的权限记录
            permissions = self.db.query(SystemPermission).filter(
                SystemPermission.page_id == page_id
            ).all()
            
            entities = []
            for permission in permissions:
                entity = self.repo.get_entity_by_id(permission.entity_id)
                if entity:
                    entities.append(entity)
            
            return entities
            
        except Exception as e:
            logger.error(f"获取页面实体列表失败: {e}")
            return []
    
    def get_permission_matrix(self) -> Dict[str, Dict[str, bool]]:
        """
        获取权限矩阵（实体 x 页面）
        
        Returns:
            Dict[str, Dict[str, bool]]: 权限矩阵
            格式: {entity_id: {page_id: has_permission}}
        """
        try:
            # 获取所有实体和页面
            all_entities = (self.repo.get_entities_by_type(EntityType.DEPARTMENT) + 
                          self.repo.get_entities_by_type(EntityType.ROLE))
            all_pages = self.repo.get_all_pages()
            
            # 获取所有权限记录
            all_permissions = self.db.query(SystemPermission).all()
            
            # 构建权限映射
            permission_map = {}
            for permission in all_permissions:
                if permission.entity_id not in permission_map:
                    permission_map[permission.entity_id] = set()
                permission_map[permission.entity_id].add(permission.page_id)
            
            # 构建权限矩阵
            matrix = {}
            for entity in all_entities:
                matrix[entity.id] = {}
                entity_permissions = permission_map.get(entity.id, set())
                
                for page in all_pages:
                    matrix[entity.id][page.id] = page.id in entity_permissions
            
            return matrix
            
        except Exception as e:
            logger.error(f"获取权限矩阵失败: {e}")
            return {}
    
    def get_permission_summary(self) -> Dict[str, any]:
        """
        获取权限分配摘要信息
        
        Returns:
            Dict: 权限摘要信息
        """
        try:
            # 统计信息
            total_entities = len(self.repo.get_entities_by_type(EntityType.DEPARTMENT) + 
                               self.repo.get_entities_by_type(EntityType.ROLE))
            total_pages = len(self.repo.get_all_pages())
            total_permissions = len(self.db.query(SystemPermission).all())
            
            # 按类型统计实体
            departments_count = len(self.repo.get_entities_by_type(EntityType.DEPARTMENT))
            roles_count = len(self.repo.get_entities_by_type(EntityType.ROLE))
            
            # 统计有权限的实体数量
            entities_with_permissions = len(set(
                permission.entity_id 
                for permission in self.db.query(SystemPermission).all()
            ))
            
            # 统计被分配权限的页面数量
            pages_with_permissions = len(set(
                permission.page_id 
                for permission in self.db.query(SystemPermission).all()
            ))
            
            return {
                "total_entities": total_entities,
                "total_pages": total_pages,
                "total_permissions": total_permissions,
                "departments_count": departments_count,
                "roles_count": roles_count,
                "entities_with_permissions": entities_with_permissions,
                "pages_with_permissions": pages_with_permissions,
                "permission_coverage": {
                    "entity_coverage": entities_with_permissions / total_entities if total_entities > 0 else 0,
                    "page_coverage": pages_with_permissions / total_pages if total_pages > 0 else 0
                }
            }
            
        except Exception as e:
            logger.error(f"获取权限摘要失败: {e}")
            return {}
    
    def copy_permissions(self, source_entity_id: str, target_entity_id: str) -> bool:
        """
        复制权限从一个实体到另一个实体
        
        Args:
            source_entity_id: 源实体ID
            target_entity_id: 目标实体ID
            
        Returns:
            bool: 是否复制成功
        """
        try:
            # 获取源实体的权限
            source_permissions = self.get_entity_permission_ids(source_entity_id)
            
            if not source_permissions:
                logger.warning(f"源实体 {source_entity_id} 没有任何权限")
                return True
            
            # 为目标实体分配相同的权限
            success = self.assign_pages_to_entity(target_entity_id, list(source_permissions))
            
            if success:
                logger.info(f"成功复制权限从实体 {source_entity_id} 到 {target_entity_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"复制权限失败: {e}")
            raise
    
    def bulk_assign_permissions(self, assignments: List[Dict[str, any]]) -> Dict[str, any]:
        """
        批量分配权限
        
        Args:
            assignments: 权限分配列表
            格式: [{"entity_id": str, "page_ids": List[str]}]
            
        Returns:
            Dict: 批量操作结果
        """
        try:
            success_count = 0
            error_count = 0
            errors = []
            
            for assignment in assignments:
                entity_id = assignment.get("entity_id")
                page_ids = assignment.get("page_ids", [])
                
                if not entity_id or not page_ids:
                    error_count += 1
                    errors.append(f"无效的分配配置: {assignment}")
                    continue
                
                try:
                    self.assign_pages_to_entity(entity_id, page_ids)
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    errors.append(f"实体 {entity_id} 权限分配失败: {str(e)}")
            
            result = {
                "success_count": success_count,
                "error_count": error_count,
                "total_count": len(assignments),
                "errors": errors
            }
            
            logger.info(f"批量权限分配完成: 成功 {success_count}, 失败 {error_count}")
            return result
            
        except Exception as e:
            logger.error(f"批量权限分配失败: {e}")
            raise