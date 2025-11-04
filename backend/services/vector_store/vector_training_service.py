"""
向量数据库训练服务 - 增量训练版本
"""

import json
import time
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from sqlalchemy.orm import Session

from services.vector_store.qdrant_vector_store import qdrant_vector_store
from utils.logger import logger
from repositories.training_repository import TrainingRecordRepository
from repositories.metadata_repository import MetadataTableRepository, MetadataColumnRepository
from repositories.glossary_repository import GlossaryTermRepository
from repositories.relation_repository import RelationFieldConfigRepository


class VectorTrainingService:
    """向量数据库训练服务 - 增量训练版本

    实现基于修改时间的增量训练，只训练有变化的资源
    """

    def __init__(self, db: Session):
        """初始化向量训练服务

        Args:
            db: 数据库会话
        """
        self.db = db

        # 初始化Repository
        self.training_repo = TrainingRecordRepository(db)
        self.table_repo = MetadataTableRepository(db)
        self.column_repo = MetadataColumnRepository(db)
        self.glossary_repo = GlossaryTermRepository(db)
        self.relation_repo = RelationFieldConfigRepository(db)

        # 使用全局向量存储实例
        try:
            self.vector_store = qdrant_vector_store
            logger.info("向量存储初始化成功，使用全局实例")
        except Exception as e:
            logger.error(f"向量存储初始化失败: {e}")
            raise

    def train_vector_database(self, session_name: str = "增量向量数据库训练") -> Dict[str, Any]:
        """增量训练向量数据库

        Args:
            session_name: 训练会话名称

        Returns:
            训练结果字典
        """
        try:
            logger.info(f"开始增量向量数据库训练: {session_name}")
            start_time = time.time()

            # 获取所有需要训练的资源
            resources_to_train = self._get_resources_needing_training()

            if not resources_to_train:
                logger.info("没有需要训练的资源，训练完成")
                return {
                    "success": True,
                    "message": "没有需要训练的资源",
                    "trained_count": 0,
                    "training_time": time.time() - start_time
                }

            # 按资源类型分组训练
            trained_count = 0
            failed_count = 0

            # 1. 训练表资源（包含字段）
            table_result = self._train_table_resources(resources_to_train.get("table", []))
            trained_count += table_result["trained"]
            failed_count += table_result["failed"]

            # 2. 训练术语表资源
            glossary_result = self._train_glossary_resources(resources_to_train.get("glossary", []))
            trained_count += glossary_result["trained"]
            failed_count += glossary_result["failed"]

            # 3. 训练关联配置资源
            relation_result = self._train_relation_resources(resources_to_train.get("relation", []))
            trained_count += relation_result["trained"]
            failed_count += relation_result["failed"]

            # 5. 清理无效资源的向量数据
            self._cleanup_orphaned_vectors()

            training_time = time.time() - start_time

            result = {
                "success": failed_count == 0,
                "message": f"增量训练完成，训练了 {trained_count} 个资源",
                "trained_count": trained_count,
                "failed_count": failed_count,
                "training_time": training_time
            }

            logger.info(f"增量向量数据库训练完成: {result}")
            return result

        except Exception as e:
            logger.error(f"增量向量数据库训练失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "trained_count": 0,
                "failed_count": 0
            }

    def _get_resources_needing_training(self) -> Dict[str, List[Dict]]:
        """获取需要训练的资源列表

        Returns:
            按资源类型分组的需要训练的资源列表
        """
        resources = {
            "table": [],
            "glossary": [],
              "relation": []
        }

        try:
            # 1. 检查表资源
            tables = self.table_repo.get_all()
            for table in tables:
                # 获取表的最后修改时间（包含字段）
                last_modified = self._get_table_last_modified_time(table.id)

                if self.training_repo.needs_training("table", table.id, last_modified):
                    resources["table"].append({
                        "id": table.id,
                        "name": table.name,
                        "last_modified": last_modified
                    })

            # 2. 检查术语表资源（只检查非基础术语）
            glossaries = self.glossary_repo.get_non_basic_terms()  # 改为只获取非基础术语
            for glossary in glossaries:
                if self.training_repo.needs_training("glossary", glossary.id, glossary.updated_at):
                    resources["glossary"].append({
                        "id": glossary.id,
                        "name": glossary.name,
                        "last_modified": glossary.updated_at
                    })

            # 3. 检查关联配置资源
            relations = self.relation_repo.get_all()
            for relation in relations:
                if self.training_repo.needs_training("relation", relation.id, relation.updated_at):
                    resources["relation"].append({
                        "id": relation.id,
                        "name": f"{relation.relation_family}:{relation.relation_subfamily}",
                        "last_modified": relation.updated_at
                    })

            logger.info(f"发现需要训练的资源: 表({len(resources['table'])}), 术语({len(resources['glossary'])}), 关联({len(resources['relation'])})")

        except Exception as e:
            logger.error(f"获取需要训练的资源失败: {e}")

        return resources

    def _get_table_last_modified_time(self, table_id: int) -> datetime:
        """获取表的最后修改时间（包含字段）

        Args:
            table_id: 表ID

        Returns:
            最后修改时间
        """
        try:
            table = self.table_repo.get_by_id(table_id)
            columns = self.column_repo.get_by_table_id(table_id)

            # 取表和所有字段的最新修改时间
            all_times = [table.updated_at] if table else []
            all_times.extend([col.updated_at for col in columns])

            return max(all_times) if all_times else datetime.now()
        except Exception as e:
            logger.error(f"获取表 {table_id} 的最后修改时间失败: {e}")
            return datetime.now()

    def _train_table_resources(self, tables: List[Dict]) -> Dict[str, int]:
        """训练表资源

        Args:
            tables: 需要训练的表列表

        Returns:
            训练结果统计
        """
        trained = 0
        failed = 0

        for table_info in tables:
            try:
                table_id = table_info["id"]
                table_name = table_info["name"]

                # 确保训练记录存在（新资源会创建记录）
                self.training_repo.create_or_update_record("table", table_id, table_info["last_modified"])

                # 标记为正在训练
                self.training_repo.mark_as_training("table", table_id)

                # 删除旧的向量数据
                self._delete_vector_by_resource("table", table_id)

                # 生成新的文档
                document, metadata = self._generate_table_document(table_id)

                if document:
                    # 添加到向量数据库
                    vector_ids = self.vector_store.add(documents=[document], metadatas=[metadata])
                    vector_id = vector_ids[0] if vector_ids else ""

                    # 更新训练记录
                    self.training_repo.update_training_time("table", table_id, vector_id)
                    trained += 1
                    logger.debug(f"成功训练表: {table_name}")
                else:
                    self.training_repo.mark_as_failed("table", table_id)
                    failed += 1
                    logger.warning(f"生成表文档失败: {table_name}")

            except Exception as e:
                failed += 1
                logger.error(f"训练表资源失败: {e}")
                if "table_id" in locals():
                    self.training_repo.mark_as_failed("table", table_id)

        return {"trained": trained, "failed": failed}

    def _train_glossary_resources(self, glossaries: List[Dict]) -> Dict[str, int]:
        """训练术语表资源

        Args:
            glossaries: 需要训练的术语表列表

        Returns:
            训练结果统计
        """
        trained = 0
        failed = 0

        for glossary_info in glossaries:
            try:
                glossary_id = glossary_info["id"]
                glossary_name = glossary_info["name"]

                # 确保训练记录存在（新资源会创建记录）
                self.training_repo.create_or_update_record("glossary", glossary_id, glossary_info["last_modified"])

                # 标记为正在训练
                self.training_repo.mark_as_training("glossary", glossary_id)

                # 删除旧的向量数据
                self._delete_vector_by_resource("glossary", glossary_id)

                # 生成新的文档
                document, metadata = self._generate_glossary_document(glossary_id)

                if document:
                    # 添加到向量数据库
                    vector_ids = self.vector_store.add(documents=[document], metadatas=[metadata])
                    vector_id = vector_ids[0] if vector_ids else ""

                    # 更新训练记录
                    self.training_repo.update_training_time("glossary", glossary_id, vector_id)
                    trained += 1
                    logger.debug(f"成功训练术语: {glossary_name}")
                else:
                    self.training_repo.mark_as_failed("glossary", glossary_id)
                    failed += 1
                    logger.warning(f"生成术语文档失败: {glossary_name}")

            except Exception as e:
                failed += 1
                logger.error(f"训练术语资源失败: {e}")
                if "glossary_id" in locals():
                    self.training_repo.mark_as_failed("glossary", glossary_id)

        return {"trained": trained, "failed": failed}

    
    def _train_relation_resources(self, relations: List[Dict]) -> Dict[str, int]:
        """训练关联配置资源

        Args:
            relations: 需要训练的关联配置列表

        Returns:
            训练结果统计
        """
        trained = 0
        failed = 0

        for relation_info in relations:
            try:
                relation_id = relation_info["id"]
                relation_name = relation_info["name"]

                # 确保训练记录存在（新资源会创建记录）
                self.training_repo.create_or_update_record("relation", relation_id, relation_info["last_modified"])

                # 标记为正在训练
                self.training_repo.mark_as_training("relation", relation_id)

                # 删除旧的向量数据
                self._delete_vector_by_resource("relation", relation_id)

                # 生成新的文档
                document, metadata = self._generate_relation_document(relation_id)

                if document:
                    # 添加到向量数据库
                    vector_ids = self.vector_store.add(documents=[document], metadatas=[metadata])
                    vector_id = vector_ids[0] if vector_ids else ""

                    # 更新训练记录
                    self.training_repo.update_training_time("relation", relation_id, vector_id)
                    trained += 1
                    logger.debug(f"成功训练关联: {relation_name}")
                else:
                    self.training_repo.mark_as_failed("relation", relation_id)
                    failed += 1
                    logger.warning(f"生成关联文档失败: {relation_name}")

            except Exception as e:
                failed += 1
                logger.error(f"训练关联资源失败: {e}")
                if "relation_id" in locals():
                    self.training_repo.mark_as_failed("relation", relation_id)

        return {"trained": trained, "failed": failed}

    def _generate_table_document(self, table_id: int) -> Tuple[str, Dict]:
        """生成表文档

        Args:
            table_id: 表ID

        Returns:
            (文档内容, 元数据)
        """
        try:
            table = self.table_repo.get_by_id(table_id)
            if not table:
                return "", {}

            columns = self.column_repo.get_by_table_id(table_id)

            # 构建表结构描述

            comment = ''
            if table.comment:
                comment = f"表描述: {table.comment}"

            doc_lines = [f"表名: {table.name} {comment}", "字段信息:"]

            for col in columns:
                col_name = col.name
                col_type = col.business_type or col.type
                col_comment = col.comment

                relation_info = ''
                if col.relation_config_id:
                    relation_info = f'关联ID: {col.relation_config_id}'

                col_line = f"  - {col_name} ({col_type}) 描述: {col_comment} {relation_info}"

                doc_lines.append(col_line)

            document = "\n".join(doc_lines)

            # 构建元数据
            metadata = {
                "resource_type": "table",
                "resource_id": table_id,
                "table_name": table.name,
                "column_count": len(columns)
            }

            return document, metadata

        except Exception as e:
            logger.error(f"生成表文档失败 {table_id}: {e}")
            return "", {}

    def _generate_glossary_document(self, glossary_id: int) -> Tuple[str, Dict]:
        """生成术语表文档

        Args:
            glossary_id: 术语ID

        Returns:
            (文档内容, 元数据)
        """
        try:
            glossary = self.glossary_repo.get_by_id(glossary_id)
            if not glossary:
                return "", {}

            # 解析content JSON
            try:
                content = json.loads(glossary.content) if glossary.content else {}
            except:
                content = {}

            # 构建术语描述
            doc_lines = []

            if glossary.type == "concept":
                doc_lines.append(f"术语: {glossary.name} 词语解释: {content.get('content', '')}")
            elif glossary.type == "sql_qa":
                doc_lines.append(f"术语: {glossary.name} 说明: {content.get('remark', '')}")
                doc_lines.append(f"问题: {content.get('question', '')}")
                doc_lines.append(f"回答SQL: {content.get('answer', '')}")
            elif glossary.type == "dict_mapping":
                doc_lines.append(f"术语: {glossary.name} 字段转换 字段名: {content.get('col_name', '')}：")
                doc_lines.append(f"转换规则: {content.get('dict_map', '')}")

            document = "\n".join(doc_lines)

            # 构建元数据
            metadata = {
                "resource_type": "glossary",
                "resource_id": glossary_id,
                "term": glossary.name,
                "glossary_type": glossary.type
            }

            return document, metadata

        except Exception as e:
            logger.error(f"生成术语文档失败 {glossary_id}: {e}")
            return "", {}

    
    def _generate_relation_document(self, relation_id: int) -> Tuple[str, Dict]:
        """生成关联配置文档

        Args:
            relation_id: 关联ID

        Returns:
            (文档内容, 元数据)
        """
        try:
            relation = self.relation_repo.get_by_id(relation_id)
            if not relation:
                return "", {}

            # 构建关联配置描述
            doc_lines = [f"关系家族: {relation.relation_family}"]
            doc_lines.append(f"子家族: {relation.relation_subfamily}")
            if relation.relation_desc:
                doc_lines.append(f"描述: {relation.relation_desc}")

            document = "\n".join(doc_lines)

            # 构建元数据
            metadata = {
                "resource_type": "relation",
                "resource_id": relation_id,
                "family_name": relation.relation_family,
                "sub_family_name": relation.relation_subfamily
            }

            return document, metadata

        except Exception as e:
            logger.error(f"生成关联文档失败 {relation_id}: {e}")
            return "", {}

    def _delete_vector_by_resource(self, resource_type: str, resource_id: int):
        """删除指定资源的向量数据

        Args:
            resource_type: 资源类型
            resource_id: 资源ID
        """
        try:
            # 根据元数据删除向量数据
            # 这里需要根据向量存储的实现来删除特定资源的数据
            # 如果向量存储支持按元数据删除，可以这样实现：
            # self.vector_store.delete(where={"resource_type": resource_type, "resource_id": resource_id})

            # 临时方案：获取训练记录中的vector_id，然后删除
            record = self.training_repo.get_by_resource(resource_type, resource_id)
            if record and record.vector_id:
                try:
                    self.vector_store.delete(ids=[record.vector_id])
                    logger.debug(f"删除向量数据: {resource_type}:{resource_id}")
                except Exception as e:
                    logger.warning(f"删除向量数据失败: {e}")

        except Exception as e:
            logger.error(f"删除向量数据失败 {resource_type}:{resource_id}: {e}")

    def _cleanup_orphaned_vectors(self):
        """清理无效资源的向量数据"""
        try:
            # 获取当前有效的资源ID列表
            valid_resources = {
                "table": [t.id for t in self.table_repo.get_all()],
                "glossary": [g.id for g in self.glossary_repo.get_all()],
                "relation": [r.id for r in self.relation_repo.get_all()]
            }

            # 清理无效的训练记录
            deleted_count = self.training_repo.cleanup_orphaned_records(valid_resources)

            if deleted_count > 0:
                logger.info(f"清理了 {deleted_count} 条无效的训练记录")

        except Exception as e:
            logger.error(f"清理无效向量数据失败: {e}")

    def get_training_status(self) -> Dict[str, Any]:
        """获取训练状态信息

        Returns:
            训练状态字典
        """
        try:
            # 获取训练统计
            stats = self.training_repo.get_statistics()

            # 获取向量数据库文档数量
            vector_count = 0
            try:
                vector_count = self.vector_store.count()
            except Exception as e:
                logger.warning(f"获取向量数据库文档数量失败: {e}")

            return {
                "training_records": stats,
                "vector_database": {
                    "document_count": vector_count
                }
            }

        except Exception as e:
            logger.error(f"获取训练状态失败: {e}")
            return {"error": str(e)}