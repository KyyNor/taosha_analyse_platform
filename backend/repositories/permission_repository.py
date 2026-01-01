"""
权限管理数据访问层
"""

from typing import List, Optional, Set
from sqlalchemy.orm import Session
from sqlalchemy import and_
from models.permission_models import SystemEntity, SystemPage, SystemPermission, SystemLoginRecord, EntityType
from utils.logger import logger


class PermissionRepository:
    """权限管理数据访问层"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # SystemEntity 相关方法
    def get_entity_by_id(self, entity_id: str) -> Optional[SystemEntity]:
        """根据ID获取实体"""
        return self.db.query(SystemEntity).filter(SystemEntity.id == entity_id).first()
    
    def get_entity_by_code_and_type(self, code: str, entity_type: EntityType) -> Optional[SystemEntity]:
        """根据编码和类型获取实体"""
        return self.db.query(SystemEntity).filter(
            and_(SystemEntity.code == code, SystemEntity.type == entity_type)
        ).first()
    
    def get_entities_by_type(self, entity_type: EntityType) -> List[SystemEntity]:
        """根据类型获取实体列表"""
        return self.db.query(SystemEntity).filter(SystemEntity.type == entity_type).all()
    
    def get_entities_by_codes(self, codes: List[str], entity_type: EntityType) -> List[SystemEntity]:
        """根据编码列表和类型获取实体"""
        return self.db.query(SystemEntity).filter(
            and_(SystemEntity.code.in_(codes), SystemEntity.type == entity_type)
        ).all()
    
    def create_entity(self, entity: SystemEntity) -> SystemEntity:
        """创建实体"""
        self.db.add(entity)
        self.db.flush()
        return entity
    
    def update_entity(self, entity: SystemEntity) -> SystemEntity:
        """更新实体"""
        self.db.merge(entity)
        self.db.flush()
        return entity
    
    def delete_entity(self, entity_id: str) -> bool:
        """删除实体"""
        entity = self.get_entity_by_id(entity_id)
        if entity:
            self.db.delete(entity)
            self.db.flush()
            return True
        return False
    
    # SystemPage 相关方法
    def get_page_by_id(self, page_id: str) -> Optional[SystemPage]:
        """根据ID获取页面"""
        return self.db.query(SystemPage).filter(SystemPage.id == page_id).first()
    
    def get_page_by_path(self, path: str) -> Optional[SystemPage]:
        """根据路径获取页面"""
        return self.db.query(SystemPage).filter(SystemPage.path == path).first()
    
    def get_all_pages(self) -> List[SystemPage]:
        """获取所有页面"""
        return self.db.query(SystemPage).all()
    
    def create_page(self, page: SystemPage) -> SystemPage:
        """创建页面"""
        self.db.add(page)
        self.db.flush()
        return page
    
    def update_page(self, page: SystemPage) -> SystemPage:
        """更新页面"""
        self.db.merge(page)
        self.db.flush()
        return page
    
    def delete_page(self, page_id: str) -> bool:
        """删除页面"""
        page = self.get_page_by_id(page_id)
        if page:
            self.db.delete(page)
            self.db.flush()
            return True
        return False
    
    # SystemPermission 相关方法
    def get_permissions_by_entity_id(self, entity_id: str) -> List[SystemPermission]:
        """根据实体ID获取权限列表"""
        return self.db.query(SystemPermission).filter(SystemPermission.entity_id == entity_id).all()
    
    def get_permissions_by_entity_ids(self, entity_ids: List[str]) -> List[SystemPermission]:
        """根据实体ID列表获取权限列表"""
        return self.db.query(SystemPermission).filter(SystemPermission.entity_id.in_(entity_ids)).all()
    
    def get_page_paths_by_entity_ids(self, entity_ids: List[str]) -> Set[str]:
        """根据实体ID列表获取页面路径集合"""
        permissions = self.db.query(SystemPermission).join(SystemPage).filter(
            SystemPermission.entity_id.in_(entity_ids)
        ).all()
        return {permission.page.path for permission in permissions}
    
    def create_permission(self, permission: SystemPermission) -> SystemPermission:
        """创建权限"""
        self.db.add(permission)
        self.db.flush()
        return permission
    
    def delete_permissions_by_entity_id(self, entity_id: str) -> int:
        """删除实体的所有权限"""
        count = self.db.query(SystemPermission).filter(SystemPermission.entity_id == entity_id).count()
        self.db.query(SystemPermission).filter(SystemPermission.entity_id == entity_id).delete()
        self.db.flush()
        return count
    
    def delete_permission(self, entity_id: str, page_id: str) -> bool:
        """删除特定权限"""
        permission = self.db.query(SystemPermission).filter(
            and_(SystemPermission.entity_id == entity_id, SystemPermission.page_id == page_id)
        ).first()
        if permission:
            self.db.delete(permission)
            self.db.flush()
            return True
        return False
    
    # SystemLoginRecord 相关方法
    def get_login_record_by_user_id(self, user_id: str) -> Optional[SystemLoginRecord]:
        """根据用户ID获取登录记录"""
        return self.db.query(SystemLoginRecord).filter(SystemLoginRecord.user_id == user_id).first()
    
    def get_all_login_records(self) -> List[SystemLoginRecord]:
        """获取所有登录记录"""
        return self.db.query(SystemLoginRecord).order_by(SystemLoginRecord.last_login_time.desc()).all()
    
    def create_or_update_login_record(self, record: SystemLoginRecord) -> SystemLoginRecord:
        """创建或更新登录记录"""
        existing = self.get_login_record_by_user_id(record.user_id)
        if existing:
            # 更新现有记录
            existing.user_name = record.user_name
            existing.branch_no = record.branch_no
            existing.branch_name = record.branch_name
            existing.role_id_list = record.role_id_list
            existing.role_name_list = record.role_name_list
            existing.last_login_time = record.last_login_time
            self.db.flush()
            return existing
        else:
            # 创建新记录
            self.db.add(record)
            self.db.flush()
            return record