"""
元数据相关的Repository
"""

from typing import List, Optional
from sqlalchemy.orm import joinedload
from sqlalchemy import and_, or_
from utils.logger import logger
from .base_repository import BaseRepository
from models.metadata_models import MetadataTable, MetadataColumn


class MetadataTableRepository(BaseRepository[MetadataTable]):
    """元数据表Repository"""

    def __init__(self):
        super().__init__(MetadataTable)

    def get_by_name(self, name: str) -> Optional[MetadataTable]:
        """根据表名获取记录"""
        try:
            with self.get_db_session() as db:
                return db.query(MetadataTable).filter(MetadataTable.name == name).first()
        except Exception as e:
            logger.error(f"根据表名获取元数据表失败: {e}")
            raise

    def get_available_tables(self) -> List[MetadataTable]:
        """获取所有可用的表（is_available = 0）"""
        try:
            with self.get_db_session() as db:
                return db.query(MetadataTable).filter(MetadataTable.is_available == 0).all()
        except Exception as e:
            logger.error(f"获取可用元数据表失败: {e}")
            raise

    def get_with_columns(self, table_id: int) -> Optional[MetadataTable]:
        """获取表及其所有列"""
        try:
            with self.get_db_session() as db:
                result = db.query(MetadataTable)\
                           .options(joinedload(MetadataTable.columns))\
                           .filter(MetadataTable.id == table_id)\
                           .first()
                if result:
                    # 先分离关联的列对象
                    if hasattr(result, 'columns') and result.columns:
                        for column in result.columns:
                            if column is not None:
                                db.expunge(column)
                    # 再分离表对象
                    db.expunge(result)
                return result
        except Exception as e:
            logger.error(f"获取表及其列信息失败: {e}")
            raise

    def get_all_with_columns(self) -> List[MetadataTable]:
        """获取所有表及其列信息"""
        try:
            with self.get_db_session() as db:
                results = db.query(MetadataTable)\
                            .options(joinedload(MetadataTable.columns))\
                            .all()
                # 将所有对象从会话中分离，避免会话关闭后访问出错
                for table in results:
                    # 先分离关联的列对象
                    if hasattr(table, 'columns') and table.columns:
                        for column in table.columns:
                            if column is not None:
                                db.expunge(column)
                    # 再分离表对象
                    db.expunge(table)
                return results
        except Exception as e:
            logger.error(f"获取所有表及其列信息失败: {e}")
            raise

    def search_tables(self, query: str) -> List[MetadataTable]:
        """搜索表（按名称或注释）"""
        try:
            with self.get_db_session() as db:
                return db.query(MetadataTable)\
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

    def get_db_session(self):
        """获取数据库会话"""
        from models.base import get_db_session
        return get_db_session()


class MetadataColumnRepository(BaseRepository[MetadataColumn]):
    """元数据列Repository"""

    def __init__(self):
        super().__init__(MetadataColumn)

    def get_by_table_id(self, table_id: int) -> List[MetadataColumn]:
        """根据表ID获取所有列"""
        try:
            with self.get_db_session() as db:
                return db.query(MetadataColumn)\
                         .filter(MetadataColumn.table_id == table_id)\
                         .all()
        except Exception as e:
            logger.error(f"根据表ID获取列失败: {e}")
            raise

    def get_by_table_and_name(self, table_id: int, name: str) -> Optional[MetadataColumn]:
        """根据表ID和列名获取列"""
        try:
            with self.get_db_session() as db:
                return db.query(MetadataColumn)\
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
            with self.get_db_session() as db:
                return db.query(MetadataColumn)\
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
            with self.get_db_session() as db:
                return db.query(MetadataColumn)\
                         .filter(MetadataColumn.relation_config_id == relation_config_id)\
                         .all()
        except Exception as e:
            logger.error(f"根据关联配置ID获取列失败: {e}")
            raise

    def search_columns(self, query: str) -> List[MetadataColumn]:
        """搜索列（按名称、类型或注释）"""
        try:
            with self.get_db_session() as db:
                return db.query(MetadataColumn)\
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

    def get_db_session(self):
        """获取数据库会话"""
        from models.base import get_db_session
        return get_db_session()