"""
元数据相关的Repository
"""

from typing import List, Optional
from sqlalchemy.orm import joinedload, Session
from sqlalchemy import and_, or_
from utils.logger import logger
from .base_repository import BaseRepository
from models.metadata_models import MetadataTable, MetadataColumn, MetadataKnowledgeDocument, MetadataKnowledgeFragment


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


class KnowledgeDocumentRepository(BaseRepository[MetadataKnowledgeDocument]):
    """知识文档Repository"""

    def __init__(self, db: Session):
        super().__init__(MetadataKnowledgeDocument, db)

    def get_by_title(self, title: str) -> Optional[MetadataKnowledgeDocument]:
        """根据标题获取文档"""
        try:
            return self.db.query(MetadataKnowledgeDocument).filter(MetadataKnowledgeDocument.title == title).first()
        except Exception as e:
            logger.error(f"根据标题获取知识文档失败: {e}")
            raise

    def get_with_fragments(self, document_id: int) -> Optional[MetadataKnowledgeDocument]:
        """获取文档及其所有片段"""
        try:
            from sqlalchemy.orm import joinedload
            result = self.db.query(MetadataKnowledgeDocument)\
                       .options(joinedload(MetadataKnowledgeDocument.fragments))\
                       .filter(MetadataKnowledgeDocument.id == document_id)\
                       .first()
            return result
        except Exception as e:
            logger.error(f"获取文档及其片段失败: {e}")
            raise

    def get_all_with_fragments(self) -> List[MetadataKnowledgeDocument]:
        """获取所有文档及其片段信息"""
        try:
            from sqlalchemy.orm import joinedload
            results = self.db.query(MetadataKnowledgeDocument)\
                        .options(joinedload(MetadataKnowledgeDocument.fragments))\
                        .all()
            return results
        except Exception as e:
            logger.error(f"获取所有文档及其片段失败: {e}")
            raise

    def search_documents(self, query: str) -> List[MetadataKnowledgeDocument]:
        """搜索文档（按标题或内容）"""
        try:
            return self.db.query(MetadataKnowledgeDocument)\
                     .filter(
                         or_(
                             MetadataKnowledgeDocument.title.contains(query),
                             MetadataKnowledgeDocument.raw_content.contains(query)
                         )
                     )\
                     .all()
        except Exception as e:
            logger.error(f"搜索知识文档失败: {e}")
            raise

    def get_by_source_type(self, source_type: str) -> List[MetadataKnowledgeDocument]:
        """根据源类型获取文档"""
        try:
            return self.db.query(MetadataKnowledgeDocument)\
                     .filter(MetadataKnowledgeDocument.source_type == source_type)\
                     .all()
        except Exception as e:
            logger.error(f"根据源类型获取文档失败: {e}")
            raise

    def update_fragment_count(self, document_id: int, count: int) -> Optional[MetadataKnowledgeDocument]:
        """更新文档的片段数量"""
        try:
            return self.update(document_id, fragment_count=count)
        except Exception as e:
            logger.error(f"更新文档片段数量失败: {e}")
            raise


class KnowledgeFragmentRepository(BaseRepository[MetadataKnowledgeFragment]):
    """知识片段Repository"""

    def __init__(self, db: Session):
        super().__init__(MetadataKnowledgeFragment, db)

    def get_by_document_id(self, document_id: int) -> List[MetadataKnowledgeFragment]:
        """根据文档ID获取所有片段"""
        try:
            return self.db.query(MetadataKnowledgeFragment)\
                     .filter(MetadataKnowledgeFragment.document_id == document_id)\
                     .all()
        except Exception as e:
            logger.error(f"根据文档ID获取片段失败: {e}")
            raise

    def get_by_document_id_paginated(self, document_id: int, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """根据文档ID分页获取片段"""
        try:
            query = self.db.query(MetadataKnowledgeFragment)\
                     .filter(MetadataKnowledgeFragment.document_id == document_id)

            # 计算总数
            total = query.count()

            # 应用分页
            offset = (page - 1) * page_size
            items = query.offset(offset).limit(page_size).all()

            return {
                'items': items,
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': (total + page_size - 1) // page_size
            }
        except Exception as e:
            logger.error(f"根据文档ID分页获取片段失败: {e}")
            raise

    def get_by_generation_method(self, generation_method: str) -> List[MetadataKnowledgeFragment]:
        """根据生成方式获取片段"""
        try:
            return self.db.query(MetadataKnowledgeFragment)\
                     .filter(MetadataKnowledgeFragment.generation_method == generation_method)\
                     .all()
        except Exception as e:
            logger.error(f"根据生成方式获取片段失败: {e}")
            raise

    def search_fragments(self, query: str) -> List[MetadataKnowledgeFragment]:
        """搜索片段（按标题、内容或摘要）"""
        try:
            return self.db.query(MetadataKnowledgeFragment)\
                     .filter(
                         or_(
                             MetadataKnowledgeFragment.title.contains(query),
                             MetadataKnowledgeFragment.content.contains(query),
                             MetadataKnowledgeFragment.summary.contains(query)
                         )
                     )\
                     .all()
        except Exception as e:
            logger.error(f"搜索知识片段失败: {e}")
            raise

    def delete_by_document_id(self, document_id: int) -> int:
        """删除文档的所有片段"""
        try:
            count = self.db.query(MetadataKnowledgeFragment)\
                     .filter(MetadataKnowledgeFragment.document_id == document_id)\
                     .delete()
            logger.info(f"删除文档 {document_id} 的所有片段，共 {count} 条")
            return count
        except Exception as e:
            logger.error(f"删除文档片段失败: {e}")
            raise

    def get_selected_fragments(self, fragment_ids: List[int]) -> List[MetadataKnowledgeFragment]:
        """获取选中的片段"""
        try:
            return self.db.query(MetadataKnowledgeFragment)\
                     .filter(MetadataKnowledgeFragment.id.in_(fragment_ids))\
                     .all()
        except Exception as e:
            logger.error(f"获取选中片段失败: {e}")
            raise

    def bulk_create(self, fragments_data: List[Dict[str, Any]]) -> List[MetadataKnowledgeFragment]:
        """批量创建片段"""
        try:
            fragments = [MetadataKnowledgeFragment(**data) for data in fragments_data]
            self.db.add_all(fragments)
            self.db.commit()
            for fragment in fragments:
                self.db.refresh(fragment)
            logger.info(f"批量创建 {len(fragments)} 个知识片段成功")
            return fragments
        except Exception as e:
            logger.error(f"批量创建知识片段失败: {e}")
            self.db.rollback()
            raise