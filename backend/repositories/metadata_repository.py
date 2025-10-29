"""
元数据相关的Repository
"""

from typing import List, Optional
from sqlalchemy.orm import joinedload, Session
from sqlalchemy import and_, or_
from utils.logger import logger
from .base_repository import BaseRepository
from models.metadata_models import MetadataTable, MetadataColumn


class MetadataTableRepository(BaseRepository[MetadataTable]):
    """元数据表Repository"""

    def __init__(self, db: Session):
        super().__init__(MetadataTable, db)

    def get_by_name(self, name: str) -> Optional[MetadataTable]:
        """根据表名获取记录"""
        try:
            return self.db.query(MetadataTable).filter(MetadataTable.name == name).first()
        except Exception as e:
            logger.error(f"根据表名获取元数据表失败: {e}")
            raise

    def get_filter_tables_with_columns(self, is_available: str, include_fields: bool, table_name_filter: str) -> List[MetadataTable]:
        """获取所有表及其列信息"""
        try:
            results = self.db.query(MetadataTable)
            if is_available == '1':
                results = results.filter(MetadataTable.is_available == 0)
            elif is_available == '0':
                results = results.filter(MetadataTable.is_available == 1)

            if include_fields:
                results = results.options(joinedload(MetadataTable.columns))

            if table_name_filter is not None and len(table_name_filter) > 0:
                results = results.filter(MetadataTable.name.ilike(f"%{table_name_filter}%"))

            results = results.all()

            return results
        except Exception as e:
            logger.error(f"获取所有表及其列信息失败: {e}")
            raise

    def get_with_columns(self, table_id: int) -> Optional[MetadataTable]:
        """获取表及其所有列"""
        try:
            result = self.db.query(MetadataTable)\
                       .options(joinedload(MetadataTable.columns))\
                       .filter(MetadataTable.id == table_id)\
                       .first()
            return result
        except Exception as e:
            logger.error(f"获取表及其列信息失败: {e}")
            raise

    def get_all_with_columns(self) -> List[MetadataTable]:
        """获取所有表及其列信息"""
        try:
            results = self.db.query(MetadataTable)\
                        .options(joinedload(MetadataTable.columns))\
                        .all()
            return results
        except Exception as e:
            logger.error(f"获取所有表及其列信息失败: {e}")
            raise

    def search_tables(self, query: str) -> List[MetadataTable]:
        """搜索表（按名称或注释）"""
        try:
            return self.db.query(MetadataTable)\
                     .filter(
                         or_(
                             MetadataTable.name.contains(query),
                             MetadataTable.comment.contains(query)
                         )
                     )\
                     .all()
        except Exception as e:
            logger.error(f"搜索元数据表失败: {e}")
            raise


class MetadataColumnRepository(BaseRepository[MetadataColumn]):
    """元数据列Repository"""

    def __init__(self, db: Session):
        super().__init__(MetadataColumn, db)

    def get_by_table_id(self, table_id: int) -> List[MetadataColumn]:
        """根据表ID获取所有列"""
        try:
            return self.db.query(MetadataColumn)\
                     .filter(MetadataColumn.table_id == table_id)\
                     .all()
        except Exception as e:
            logger.error(f"根据表ID获取列失败: {e}")
            raise

    def get_by_table_and_name(self, table_id: int, name: str) -> Optional[MetadataColumn]:
        """根据表ID和列名获取列"""
        try:
            return self.db.query(MetadataColumn)\
                     .filter(
                         and_(
                             MetadataColumn.table_id == table_id,
                             MetadataColumn.name == name
                         )
                     )\
                     .first()
        except Exception as e:
            logger.error(f"根据表ID和列名获取列失败: {e}")
            raise

    def get_available_columns(self, table_id: int) -> List[MetadataColumn]:
        """获取表中所有可用的列"""
        try:
            return self.db.query(MetadataColumn)\
                     .filter(
                         and_(
                             MetadataColumn.table_id == table_id,
                             MetadataColumn.is_available == 0
                         )
                     )\
                     .all()
        except Exception as e:
            logger.error(f"获取可用列失败: {e}")
            raise

    def get_by_relation_config_id(self, relation_config_id: int) -> List[MetadataColumn]:
        """根据关联配置ID获取列"""
        try:
            return self.db.query(MetadataColumn)\
                     .filter(MetadataColumn.relation_config_id == relation_config_id)\
                     .all()
        except Exception as e:
            logger.error(f"根据关联配置ID获取列失败: {e}")
            raise

    def search_columns(self, query: str) -> List[MetadataColumn]:
        """搜索列（按名称、类型或注释）"""
        try:
            return self.db.query(MetadataColumn)\
                     .filter(
                         or_(
                             MetadataColumn.name.contains(query),
                             MetadataColumn.type.contains(query),
                             MetadataColumn.comment.contains(query),
                             MetadataColumn.business_type.contains(query)
                         )
                     )\
                     .all()
        except Exception as e:
            logger.error(f"搜索列失败: {e}")
            raise