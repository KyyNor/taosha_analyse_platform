"""
数据主题相关的Repository
"""

from typing import List, Optional
from sqlalchemy.orm import joinedload, Session
from sqlalchemy import and_, or_
from utils.logger import logger
from .base_repository import BaseRepository
from models.theme_models import DataTheme, ThemeTableRelation


class DataThemeRepository(BaseRepository[DataTheme]):
    """数据主题Repository"""

    def __init__(self, db: Session):
        super().__init__(DataTheme, db)

    def get_by_name(self, name: str) -> Optional[DataTheme]:
        """根据主题名称获取记录"""
        try:
            result = self.db.query(DataTheme).filter(DataTheme.theme_name == name).first()
            return result
        except Exception as e:
            logger.error(f"根据名称获取数据主题失败: {e}")
            raise

    def get_by_type(self, theme_type: str) -> List[DataTheme]:
        """根据主题类型获取列表"""
        try:
            results = self.db.query(DataTheme).filter(DataTheme.theme_type == theme_type).all()
            return results
        except Exception as e:
            logger.error(f"根据类型获取数据主题失败: {e}")
            raise

    def get_by_department(self, department: str) -> List[DataTheme]:
        """根据部门获取主题列表"""
        try:
            return self.db.query(DataTheme).filter(DataTheme.department == department).all()
        except Exception as e:
            logger.error(f"根据部门获取数据主题失败: {e}")
            raise

    def get_public_theme(self) -> Optional[DataTheme]:
        """获取通用主题"""
        try:
            result = self.db.query(DataTheme).filter(DataTheme.theme_type == 'public').first()
            return result
        except Exception as e:
            logger.error(f"获取通用主题失败: {e}")
            raise

    def get_with_tables(self, theme_id: int) -> Optional[DataTheme]:
        """获取主题及其关联的表"""
        try:
            return self.db.query(DataTheme)\
                     .options(joinedload(DataTheme.table_relations))\
                     .filter(DataTheme.id == theme_id)\
                     .first()
        except Exception as e:
            logger.error(f"获取主题及其关联表失败: {e}")
            raise

    def search_themes(self, query: str) -> List[DataTheme]:
        """搜索主题（按名称、描述或部门）"""
        try:
            return self.db.query(DataTheme)\
                     .filter(
                         or_(
                             DataTheme.theme_name.contains(query),
                             DataTheme.theme_description.contains(query),
                             DataTheme.department.contains(query)
                         )
                     )\
                     .all()
        except Exception as e:
            logger.error(f"搜索数据主题失败: {e}")
            raise



class ThemeTableRelationRepository(BaseRepository[ThemeTableRelation]):
    """主题表关联关系Repository"""

    def __init__(self, db: Session):
        super().__init__(ThemeTableRelation, db)

    def get_by_theme_id(self, theme_id: int) -> List[ThemeTableRelation]:
        """根据主题ID获取所有关联"""
        try:
            results = self.db.query(ThemeTableRelation)\
                        .filter(ThemeTableRelation.theme_id == theme_id)\
                        .all()
            return results
        except Exception as e:
            logger.error(f"根据主题ID获取关联关系失败: {e}")
            raise

    def get_by_table_id(self, table_id: int) -> List[ThemeTableRelation]:
        """根据表ID获取所有关联"""
        try:
            results = self.db.query(ThemeTableRelation)\
                        .filter(ThemeTableRelation.table_id == table_id)\
                        .all()
            return results
        except Exception as e:
            logger.error(f"根据表ID获取关联关系失败: {e}")
            raise

    def get_relation(self, theme_id: int, table_id: int) -> Optional[ThemeTableRelation]:
        """获取特定主题和表的关联关系"""
        try:
            result = self.db.query(ThemeTableRelation)\
                       .filter(
                           and_(
                               ThemeTableRelation.theme_id == theme_id,
                               ThemeTableRelation.table_id == table_id
                           )
                       )\
                       .first()
            return result
        except Exception as e:
            logger.error(f"获取关联关系失败: {e}")
            raise

    def add_table_to_theme(self, theme_id: int, table_id: int) -> ThemeTableRelation:
        """添加表到主题（如果不存在的话）"""
        try:
            # 检查是否已存在
            existing = self.get_relation(theme_id, table_id)
            if existing:
                return existing

            # 使用基础Repository的create方法
            return self.create(theme_id=theme_id, table_id=table_id)
        except Exception as e:
            logger.error(f"添加表到主题失败: {e}")
            raise

    def remove_table_from_theme(self, theme_id: int, table_id: int) -> bool:
        """从主题中移除表"""
        try:
            relation = self.db.query(ThemeTableRelation)\
                          .filter(
                              and_(
                                  ThemeTableRelation.theme_id == theme_id,
                                  ThemeTableRelation.table_id == table_id
                              )
                          )\
                          .first()
            if relation:
                self.db.delete(relation)
                return True
            return False
        except Exception as e:
            logger.error(f"从主题中移除表失败: {e}")
            raise

    def get_db_session(self):
        """获取数据库会话"""
        from models.db_base import get_db_session
        return get_db_session()