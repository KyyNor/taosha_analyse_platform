"""
向量数据库训练服务 - 增量训练版本
"""

import json
import time
from typing import List, Dict, Any, Optional, Tuple, Callable
from datetime import datetime

from sqlalchemy.orm import Session

from services.vector_store.qdrant_vector_store import qdrant_vector_store
from utils.logger import logger
from repositories.training_repository import TrainingRecordRepository
from repositories.metadata_repository import MetadataTableRepository, MetadataColumnRepository, KnowledgeFragmentRepository
from repositories.glossary_repository import GlossaryTermRepository
from repositories.relation_repository import RelationFieldConfigRepository
from repositories.fine_report_repository import FineReportRepository
from services.vector_store.schema_summary_service import SchemaSummaryService


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
        self.fine_report_repo = FineReportRepository(db)
        self.fragment_repo = KnowledgeFragmentRepository(db)

        # 使用全局向量存储实例
        try:
            self.vector_store = qdrant_vector_store
            logger.info("向量存储初始化成功，使用全局实例")
        except Exception as e:
            logger.error(f"向量存储初始化失败: {e}")
            raise

        # 初始化Schema摘要服务（包含字段值采样功能）
        try:
            self.schema_summary_service = SchemaSummaryService(db)
            logger.info("Schema摘要服务初始化成功")
        except Exception as e:
            logger.warning(f"Schema摘要服务初始化失败: {e}")
            self.schema_summary_service = None

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

            # 1. 训练表资源（包含字段，多文档模式）
            table_result = self._batch_train(
                resources_to_train.get("table", []),
                "table",
                self._generate_table_document,
                supports_multiple_docs=True
            )
            trained_count += table_result["trained"]
            failed_count += table_result["failed"]

            # 2. 训练术语表资源
            glossary_result = self._batch_train(
                resources_to_train.get("glossary", []),
                "glossary",
                self._generate_glossary_document
            )
            trained_count += glossary_result["trained"]
            failed_count += glossary_result["failed"]

            # 3. 训练关联配置资源
            relation_result = self._batch_train(
                resources_to_train.get("relation", []),
                "relation",
                self._generate_relation_document
            )
            trained_count += relation_result["trained"]
            failed_count += relation_result["failed"]

            # 4. 训练FineReport报表资源
            fine_report_result = self._batch_train(
                resources_to_train.get("fine_report", []),
                "fine_report",
                self._generate_fine_report_document
            )
            trained_count += fine_report_result["trained"]
            failed_count += fine_report_result["failed"]

            # 5. 训练知识片段资源
            fragment_result = self._batch_train(
                resources_to_train.get("knowledge_fragment", []),
                "knowledge_fragment",
                self._generate_knowledge_fragment_document
            )
            trained_count += fragment_result["trained"]
            failed_count += fragment_result["failed"]

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
            "relation": [],
            "fine_report": [],
            "knowledge_fragment": []
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

            # 4. 检查FineReport报表资源
            fine_reports = self.fine_report_repo.get_all()
            for report in fine_reports:
                if self.training_repo.needs_training("fine_report", report.id, report.updated_at):
                    resources["fine_report"].append({
                        "id": report.id,
                        "name": report.report_name,
                        "last_modified": report.updated_at
                    })

            # 5. 检查知识片段资源
            from models.metadata_models import MetadataKnowledgeFragment
            fragments = self.fragment_repo.db.query(MetadataKnowledgeFragment).all()
            for fragment in fragments:
                if self.training_repo.needs_training("knowledge_fragment", fragment.id, fragment.updated_at):
                    resources["knowledge_fragment"].append({
                        "id": fragment.id,
                        "name": fragment.title,
                        "last_modified": fragment.updated_at
                    })

            logger.info(f"发现需要训练的资源: 表({len(resources['table'])}), 术语({len(resources['glossary'])}), 关联({len(resources['relation'])}), FineReport({len(resources['fine_report'])}), 知识片段({len(resources['knowledge_fragment'])})")

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

    def _batch_train(
        self,
        resources: List[Dict],
        resource_type: str,
        doc_generator,
        supports_multiple_docs: bool = False
    ) -> Dict[str, int]:
        """通用批量训练方法

        Args:
            resources: 需要训练的资源列表
            resource_type: 资源类型 (table/glossary/relation/fine_report/knowledge_fragment)
            doc_generator: 文档生成函数，接受resource_id，返回:
                - 单文档模式: (str, Dict) 或 ""
                - 多文档模式(supports_multiple_docs=True): List[Tuple[str, Dict]]
            supports_multiple_docs: 是否支持多文档(chunks)，表资源需要设为True

        Returns:
            训练结果统计 {"trained": int, "failed": int}
        """
        trained = 0
        failed = 0

        for resource_info in resources:
            resource_id = resource_info.get("id")
            resource_name = resource_info.get("name")

            try:
                # 确保训练记录存在（新资源会创建记录）
                self.training_repo.create_or_update_record(
                    resource_type, resource_id, resource_info["last_modified"]
                )

                # 标记为正在训练
                self.training_repo.mark_as_training(resource_type, resource_id)

                # 删除旧的向量数据
                self._delete_vector_by_resource(resource_type, resource_id)

                # 生成文档
                documents = doc_generator(resource_id)

                if not documents:
                    self.training_repo.mark_as_failed(resource_type, resource_id)
                    failed += 1
                    logger.warning(f"生成文档失败: {resource_name}")
                    continue

                # 添加到向量数据库
                vector_ids = []

                if supports_multiple_docs:
                    # 多文档模式（表资源）：documents 是 List[Tuple[str, Dict]]
                    for doc_tuple in documents:
                        doc_text, doc_meta = doc_tuple
                        if doc_text:
                            ids = self.vector_store.add(
                                documents=[doc_text], metadatas=[doc_meta]
                            )
                            vector_ids.extend(ids)
                else:
                    # 单文档模式：documents 可能是 (str, Dict) 或 空字符串
                    if isinstance(documents, tuple):
                        doc_text, metadata = documents
                        if doc_text:
                            ids = self.vector_store.add(
                                documents=[doc_text], metadatas=[metadata]
                            )
                            vector_ids.extend(ids)

                # 更新训练记录（使用第一个vector_id作为主ID）
                primary_vector_id = vector_ids[0] if vector_ids else ""
                self.training_repo.update_training_time(resource_type, resource_id, primary_vector_id)

                trained += 1
                logger.debug(f"成功训练 {resource_type}: {resource_name}，生成了 {len(vector_ids)} 个chunks")

            except Exception as e:
                failed += 1
                logger.error(f"训练 {resource_type} 资源失败: {e}")
                if resource_id:
                    self.training_repo.mark_as_failed(resource_type, resource_id)

        return {"trained": trained, "failed": failed}

    def _generate_knowledge_fragment_document(self, fragment_id: int) -> Tuple[str, Dict]:
        """生成知识片段文档

        Args:
            fragment_id: 片段ID

        Returns:
            (文档内容, 元数据)
        """
        try:
            from models.metadata_models import MetadataKnowledgeFragment

            fragment = self.fragment_repo.db.query(MetadataKnowledgeFragment).filter(
                MetadataKnowledgeFragment.id == fragment_id
            ).first()

            if not fragment:
                return "", {}

            # 构建知识片段描述
            doc_lines = []

            # 添加标题
            doc_lines.append(f"知识片段: {fragment.title}")

            # 添加摘要（如果有）
            if fragment.summary:
                doc_lines.append(f"摘要: {fragment.summary}")

            # 添加内容
            doc_lines.append(f"内容: {fragment.content}")

            # 添加生成方式
            if fragment.generation_method == "auto":
                doc_lines.append("来源: AI自动生成")
            elif fragment.generation_method == "user_extraction":
                if fragment.extraction_theme:
                    doc_lines.append(f"来源: 用户主题提取 ({fragment.extraction_theme})")
                else:
                    doc_lines.append("来源: 用户主题提取")
            else:
                doc_lines.append("来源: 用户手动创建")

            # 合并所有行
            document = "\n".join(doc_lines)

            # 构建元数据
            metadata = {
                "resource_type": "knowledge_fragment",
                "resource_id": str(fragment_id),
                "title": fragment.title,
                "generation_method": fragment.generation_method,
                "document_id": str(fragment.document_id)
            }

            return document, metadata

        except Exception as e:
            logger.error(f"生成知识片段文档失败: {e}")
            return "", {}

    def _generate_table_document(self, table_id: int) -> List[Tuple[str, Dict]]:
        """生成表文档（支持分块）

        使用Schema摘要服务生成包含字段值样例、统计信息的丰富schema描述

        Args:
            table_id: 表ID

        Returns:
            [(文档内容, 元数据), ...] 列表
        """
        try:
            # 使用Schema摘要服务生成文档
            if self.schema_summary_service:
                documents = self.schema_summary_service.generate_table_summary(
                    table_id=table_id,
                    include_field_samples=True,
                    include_table_stats=True
                )

                if documents:
                    return documents
                else:
                    logger.warning(f"Schema摘要服务生成文档失败 table_id={table_id}")
                    return []

            else:
                # 降级：使用简单的表描述
                logger.warning("Schema摘要服务不可用，使用简单的表描述")
                return self._generate_simple_table_document(table_id)

        except Exception as e:
            logger.error(f"生成表文档失败 {table_id}: {e}")
            return []

    def _generate_simple_table_document(self, table_id: int) -> List[Tuple[str, Dict]]:
        """生成简单的表文档（降级方案）

        Args:
            table_id: 表ID

        Returns:
            [(文档内容, 元数据), ...] 列表
        """
        try:
            table = self.table_repo.get_by_id(table_id)
            if not table:
                return []

            columns = self.column_repo.get_by_table_id(table_id)
            available_columns = [col for col in columns if col.is_available == 0]

            # 构建基础表结构描述
            comment = ''
            if table.comment:
                comment = f"表描述: {table.comment}"

            doc_lines = [f"表名: {table.name} {comment}", "字段信息:"]

            for col in available_columns:
                col_name = col.name
                col_type = col.business_type or col.type
                col_comment = col.comment or ""

                col_line = f"  - {col_name} ({col_type}) 描述: {col_comment}"
                doc_lines.append(col_line)

            document = "\n".join(doc_lines)

            # 构建元数据
            metadata = {
                "resource_type": "table",
                "resource_id": table_id,
                "table_name": table.name,
                "column_count": len(available_columns),
                "has_field_samples": False,
                "chunk_type": "simple",
                "separated": 0
            }

            return [(document, metadata)]

        except Exception as e:
            logger.error(f"生成简单表文档失败 {table_id}: {e}")
            return []

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

    def _generate_fine_report_document(self, report_id: int) -> Tuple[str, Dict]:
        """生成FineReport报表文档

        Args:
            report_id: 报表ID

        Returns:
            (文档内容, 元数据)
        """
        try:
            report = self.fine_report_repo.get_by_id(report_id)
            if not report:
                return "", {}

            # 构建报表描述
            doc_lines = [f"报表名称: {report.report_name}"]

            # 报表类型
            report_type_name = "汇总表" if report.report_type == "summary" else "明细表"
            doc_lines.append(f"报表类型: {report_type_name}")

            # CPT文件路径
            doc_lines.append(f"CPT文件路径: {report.report_cpt_path}")

            # 设计器地址
            doc_lines.append(f"设计器地址: {report.report_design_address}")

            # 部门信息
            if report.department_id:
                doc_lines.append(f"所属部门ID: {report.department_id}")

            # 报表说明
            if report.description:
                doc_lines.append(f"报表说明: {report.description}")

            # 适用场景
            if report.usage_scenario:
                doc_lines.append(f"适用场景: {report.usage_scenario}")

            # 可用状态
            availability = "可用" if report.is_available == 0 else "不可用"
            doc_lines.append(f"状态: {availability}")

            document = "\n".join(doc_lines)

            # 构建元数据
            metadata = {
                "resource_type": "fine_report",
                "resource_id": report_id,
                "report_name": report.report_name,
                "report_type": report.report_type,
                "department_id": report.department_id if report.department_id else None,
                "is_available": report.is_available
            }

            return document, metadata

        except Exception as e:
            logger.error(f"生成报表文档失败 {report_id}: {e}")
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
                "relation": [r.id for r in self.relation_repo.get_all()],
                "fine_report": [r.id for r in self.fine_report_repo.get_all()]
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