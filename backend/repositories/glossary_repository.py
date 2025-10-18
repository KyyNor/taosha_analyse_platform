"""
术语表和提示词模板相关的Repository
"""

from typing import List, Optional
from sqlalchemy import and_, or_
from utils.logger import logger
from .base_repository import BaseRepository
from models.glossary_models import GlossaryTerm, PromptTemplate


class GlossaryTermRepository(BaseRepository[GlossaryTerm]):
    """术语表Repository"""

    def __init__(self):
        super().__init__(GlossaryTerm)

    def get_by_name(self, name: str) -> Optional[GlossaryTerm]:
        """根据术语名称获取记录"""
        try:
            with self.get_db_session() as db:
                return db.query(GlossaryTerm).filter(GlossaryTerm.name == name).first()
        except Exception as e:
            logger.error(f"根据名称获取术语失败: {e}")
            raise

    def get_by_type(self, term_type: str) -> List[GlossaryTerm]:
        """根据类型获取术语列表"""
        try:
            with self.get_db_session() as db:
                return db.query(GlossaryTerm).filter(GlossaryTerm.type == term_type).all()
        except Exception as e:
            logger.error(f"根据类型获取术语失败: {e}")
            raise

    def get_by_creator(self, creator: str) -> List[GlossaryTerm]:
        """根据创建者获取术语列表"""
        try:
            with self.get_db_session() as db:
                return db.query(GlossaryTerm).filter(GlossaryTerm.creator == creator).all()
        except Exception as e:
            logger.error(f"根据创建者获取术语失败: {e}")
            raise

    def search_terms(self, query: str) -> List[GlossaryTerm]:
        """搜索术语（按名称或内容）"""
        try:
            with self.get_db_session() as db:
                return db.query(GlossaryTerm)\
                         .filter(
                             or_(
                                 GlossaryTerm.name.contains(query),
                                 GlossaryTerm.content.contains(query)
                             )
                         )\
                         .all()
        except Exception as e:
            logger.error(f"搜索术语失败: {e}")
            raise

    def find_similar_terms(self, name: str, limit: int = 5) -> List[GlossaryTerm]:
        """查找相似的术语"""
        try:
            with self.get_db_session() as db:
                return db.query(GlossaryTerm)\
                         .filter(GlossaryTerm.name.contains(name))\
                         .limit(limit)\
                         .all()
        except Exception as e:
            logger.error(f"查找相似术语失败: {e}")
            raise


class PromptTemplateRepository(BaseRepository[PromptTemplate]):
    """提示词模板Repository"""

    def __init__(self):
        super().__init__(PromptTemplate)

    def get_by_name(self, name: str) -> Optional[PromptTemplate]:
        """根据模板名称获取记录"""
        try:
            with self.get_db_session() as db:
                return db.query(PromptTemplate).filter(PromptTemplate.name == name).first()
        except Exception as e:
            logger.error(f"根据名称获取提示词模板失败: {e}")
            raise

    def get_all_with_fields(self) -> List[PromptTemplate]:
        """获取所有模板并解析字段"""
        try:
            with self.get_db_session() as db:
                templates = db.query(PromptTemplate).all()
                # 这里可以在需要时解析fields JSON
                return templates
        except Exception as e:
            logger.error(f"获取提示词模板列表失败: {e}")
            raise

    def search_templates(self, query: str) -> List[PromptTemplate]:
        """搜索模板（按名称或内容）"""
        try:
            with self.get_db_session() as db:
                return db.query(PromptTemplate)\
                         .filter(
                             or_(
                                 PromptTemplate.name.contains(query),
                                 PromptTemplate.template.contains(query),
                                 PromptTemplate.fields.contains(query)
                             )
                         )\
                         .all()
        except Exception as e:
            logger.error(f"搜索提示词模板失败: {e}")
            raise

    def get_templates_by_field(self, field_name: str) -> List[PromptTemplate]:
        """根据字段名获取包含该字段的模板"""
        try:
            with self.get_db_session() as db:
                return db.query(PromptTemplate)\
                         .filter(PromptTemplate.fields.contains(field_name))\
                         .all()
        except Exception as e:
            logger.error(f"根据字段名获取提示词模板失败: {e}")
            raise

    def get_db_session(self):
        """获取数据库会话"""
        from models.base import get_db_session
        return get_db_session()