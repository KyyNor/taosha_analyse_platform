"""
关联字段配置相关的Repository
"""

from typing import List, Optional
from sqlalchemy import and_, or_
from utils.logger import logger
from models.db_base import get_detached_session
from .base_repository import BaseRepository
from models.relation_models import RelationFieldConfig


class RelationFieldConfigRepository(BaseRepository[RelationFieldConfig]):
    """关联字段配置Repository"""

    def __init__(self):
        super().__init__(RelationFieldConfig)

    def get_by_family_subfamily(self, family: str, subfamily: str) -> Optional[RelationFieldConfig]:
        """根据家族和子家族获取配置"""
        try:
            with get_detached_session() as db:
                return db.query(RelationFieldConfig)\
                         .filter(
                             and_(
                                 RelationFieldConfig.relation_family == family,
                                 RelationFieldConfig.relation_subfamily == subfamily
                             )
                         )\
                         .first()
        except Exception as e:
            logger.error(f"根据家族和子家族获取关联配置失败: {e}")
            raise

    def get_by_family(self, family: str) -> List[RelationFieldConfig]:
        """根据家族获取所有配置"""
        try:
            with get_detached_session() as db:
                return db.query(RelationFieldConfig)\
                         .filter(RelationFieldConfig.relation_family == family)\
                         .all()
        except Exception as e:
            logger.error(f"根据家族获取关联配置失败: {e}")
            raise

    def get_all_relation_ids(self) -> List[str]:
        """获取所有关系ID列表"""
        try:
            with get_detached_session() as db:
                configs = db.query(RelationFieldConfig).all()
                return [config.relation_id for config in configs]
        except Exception as e:
            logger.error(f"获取关系ID列表失败: {e}")
            raise

    def search_configs(self, query: str) -> List[RelationFieldConfig]:
        """搜索关联配置"""
        try:
            with get_detached_session() as db:
                return db.query(RelationFieldConfig)\
                         .filter(
                             or_(
                                 RelationFieldConfig.relation_family.contains(query),
                                 RelationFieldConfig.relation_subfamily.contains(query),
                                 RelationFieldConfig.relation_desc.contains(query)
                             )
                         )\
                         .all()
        except Exception as e:
            logger.error(f"搜索关联配置失败: {e}")
            raise

    def get_db_session(self):
        """获取数据库会话"""
        from models.db_base import get_db_session
        return get_db_session()