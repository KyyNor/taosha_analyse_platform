"""
向量数据库训练服务 - 增量训练版本
"""

import json
import time
from typing import List, Dict, Any, Optional, Tuple, Callable
from datetime import datetime

from sqlalchemy.orm import Session

from models.db_base import get_db_session
from services.vector_store.qdrant_vector_store import qdrant_vector_store
from utils.logger import logger
from repositories.training_repository import TrainingRecordRepository
from repositories.metadata_repository import MetadataTableRepository, MetadataColumnRepository
from repositories.glossary_repository import GlossaryTermRepository
from repositories.relation_repository import RelationFieldConfigRepository
from repositories.fine_report_repository import FineReportRepository
from services.vector_store.schema_summary_service import SchemaSummaryService
from utils.config import settings


class VectorTrainingService:
    """向量数据库训练服务 - 增量训练版本

    实现基于修改时间的增量训练，只训练有变化的资源

    连接管理特点：
    - 不在初始化时持有数据库连接
    - 每种资源类型使用独立的数据库连接
    - 文档生成阶段使用独立的短生命周期连接
    - 连接在使用完后立即释放，避免超时问题
    """

    def __init__(self):
        """初始化向量训练服务（不再接收 db 参数）

        连接将由各方法内部自行管理。
        """
        # 不再持有 db session
        self.db = None

        # 不再在初始化时创建 Repository，在具体使用时创建
        self._training_repo = None
        self._table_repo = None
        self._column_repo = None
        self._glossary_repo = None
        self._fine_report_repo = None
        self._fragment_repo = None

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

        注意：此方法在内部获取独立的数据库连接，使用完毕后立即释放。

        Returns:
            按资源类型分组的需要训练的资源列表，每种资源类型受配置文件控制最大数量
        """
        # 从配置获取每种资源类型的最大训练数量，默认5个
        max_docs_per_type = getattr(settings, 'vector_training_max_docs_per_type', 5) or 5

        resources = {
            "table": [],
            "glossary": [],
            "relation": [],
            "fine_report": [],
            "knowledge_fragment": []
        }

        try:
            # 在独立的 with 块中获取连接，执行所有数据库操作
            with get_db_session() as db:
                # 创建所需的 Repository
                table_repo = MetadataTableRepository(db)
                column_repo = MetadataColumnRepository(db)
                glossary_repo = GlossaryTermRepository(db)
                relation_repo = RelationFieldConfigRepository(db)
                fine_report_repo = FineReportRepository(db)
                training_repo = TrainingRecordRepository(db)

                # 1. 检查表资源
                tables = table_repo.get_all()
                for table in tables:
                    # 获取表的最后修改时间（包含字段）
                    last_modified = self._get_table_last_modified_time(table.id, table_repo, column_repo)

                    if training_repo.needs_training("table", table.id, last_modified):
                        resources["table"].append({
                            "id": table.id,
                            "name": table.name,
                            "last_modified": last_modified
                        })

                # 2. 检查术语表资源（只检查非基础术语）
                glossaries = glossary_repo.get_non_basic_terms()
                for glossary in glossaries:
                    if training_repo.needs_training("glossary", glossary.id, glossary.updated_at):
                        resources["glossary"].append({
                            "id": glossary.id,
                            "name": glossary.name,
                            "last_modified": glossary.updated_at
                        })

                # 3. 检查关联配置资源
                relations = relation_repo.get_all()
                for relation in relations:
                    if training_repo.needs_training("relation", relation.id, relation.updated_at):
                        resources["relation"].append({
                            "id": relation.id,
                            "name": f"{relation.relation_family}:{relation.relation_subfamily}",
                            "last_modified": relation.updated_at
                        })

                # 4. 检查FineReport报表资源
                fine_reports = fine_report_repo.get_all()
                for report in fine_reports:
                    if training_repo.needs_training("fine_report", report.id, report.updated_at):
                        resources["fine_report"].append({
                            "id": report.id,
                            "name": report.report_name,
                            "last_modified": report.updated_at
                        })

                # 5. 检查知识片段资源
                from models.metadata_models import MetadataKnowledgeFragment
                # 需要一个新的 session 来查询
                with get_db_session() as fragment_db:
                    fragments = fragment_db.query(MetadataKnowledgeFragment).all()
                    for fragment in fragments:
                        if training_repo.needs_training("knowledge_fragment", fragment.id, fragment.updated_at):
                            resources["knowledge_fragment"].append({
                                "id": fragment.id,
                                "name": fragment.title,
                                "last_modified": fragment.updated_at
                            })

                # 对每种资源类型应用最大数量限制
                total_found = {
                    "table": len(resources["table"]),
                    "glossary": len(resources["glossary"]),
                    "relation": len(resources["relation"]),
                    "fine_report": len(resources["fine_report"]),
                    "knowledge_fragment": len(resources["knowledge_fragment"])
                }

                for resource_type in resources:
                    if len(resources[resource_type]) > max_docs_per_type:
                        resources[resource_type] = resources[resource_type][:max_docs_per_type]

                logger.info(f"发现需要训练的资源: 表({total_found['table']}), 术语({total_found['glossary']}), 关联({total_found['relation']}), FineReport({total_found['fine_report']}), 知识片段({total_found['knowledge_fragment']})，本次将训练: 表({len(resources['table'])}), 术语({len(resources['glossary'])}), 关联({len(resources['relation'])}), FineReport({len(resources['fine_report'])}), 知识片段({len(resources['knowledge_fragment'])})，超过上限({max_docs_per_type})的将在下次训练")

        except Exception as e:
            logger.error(f"获取需要训练的资源失败: {e}")

        return resources
    

    def _get_table_last_modified_time(self, table_id: int, table_repo: MetadataTableRepository, column_repo: MetadataColumnRepository) -> datetime:
        """获取表的最后修改时间（包含字段）- 使用传入的column_repo

        Args:
            table_id: 表ID
            column_repo: 列仓储实例（必须由调用方传入）

        Returns:
            最后修改时间
        """
        try:
            # 使用传入的 column_repo，table 需要单独获取
            table = table_repo.get_by_id(table_id)
            columns = column_repo.get_by_table_id(table_id)

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
        """通用批量训练方法（三阶段连接管理）

        三阶段模式：
        1. 阶段1：获取连接 -> 执行前置数据库操作 -> 释放连接
        2. 阶段2：耗时文档生成（内部自行管理连接）
        3. 阶段3：获取连接 -> 执行后置操作 -> 释放连接

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
                # ========== 阶段1: 前置数据库操作 ==========
                # 在独立连接中执行：创建/更新训练记录、标记训练中、删除旧向量
                with get_db_session() as db:
                    training_repo = TrainingRecordRepository(db)
                    training_repo.create_or_update_record(
                        resource_type, resource_id, resource_info["last_modified"]
                    )
                    training_repo.mark_as_training(resource_type, resource_id)

                    # 获取旧记录的所有 vector_ids 用于删除
                    old_vector_ids = training_repo.get_vector_ids(resource_type, resource_id)

                    # 删除旧的向量数据（如果存在）
                    if old_vector_ids:
                        try:
                            self.vector_store.delete(ids=old_vector_ids)
                            logger.debug(f"删除了旧向量: {resource_type}:{resource_id}, 共 {len(old_vector_ids)} 个")
                        except Exception as del_err:
                            logger.warning(f"删除旧向量失败: {del_err}")

                # ========== 阶段2: 耗时文档生成 ==========
                # 这是最耗时的操作，它内部会自己管理数据库连接
                # 此阶段不持有 MySQL 连接，因此不会导致连接超时
                documents = doc_generator(resource_id)

                # ========== 阶段3: 后置数据库操作 ==========
                # 获取新的连接，执行：添加到向量数据库、更新训练完成状态
                with get_db_session() as db:
                    if not documents:
                        training_repo = TrainingRecordRepository(db)
                        training_repo.mark_as_failed(resource_type, resource_id)
                        failed += 1
                        logger.warning(f"生成文档失败: {resource_name}")
                        continue

                    training_repo = TrainingRecordRepository(db)

                    # 添加到向量数据库（Qdrant 操作，不需要 db session）
                    vector_ids = []
                    if supports_multiple_docs:
                        # 多文档模式（表资源）
                        for doc_tuple in documents:
                            doc_text, doc_meta = doc_tuple
                            if doc_text:
                                ids = self.vector_store.add(
                                    documents=[doc_text], metadatas=[doc_meta]
                                )
                                vector_ids.extend(ids)
                    else:
                        # 单文档模式
                        if isinstance(documents, tuple):
                            doc_text, metadata = documents
                            if doc_text:
                                ids = self.vector_store.add(
                                    documents=[doc_text], metadatas=[metadata]
                                )
                                vector_ids.extend(ids)

                    # 更新训练记录（保存所有 vector_ids）
                    training_repo.update_training_time(resource_type, resource_id, vector_ids)

                trained += 1
                logger.debug(f"成功训练 {resource_type}: {resource_name}，生成了 {len(vector_ids)} 个chunks")

            except Exception as e:
                failed += 1
                logger.error(f"训练 {resource_type} 资源失败: {e}")
                if resource_id:
                    try:
                        with get_db_session() as db:
                            training_repo = TrainingRecordRepository(db)
                            training_repo.mark_as_failed(resource_type, resource_id)
                    except Exception as update_err:
                        logger.error(f"更新失败状态出错: {update_err}")

        return {"trained": trained, "failed": failed}

    def _generate_knowledge_fragment_document(self, fragment_id: int) -> Tuple[str, Dict]:
        """生成知识片段文档

        注意：此方法内部获取独立的数据库连接，使用完毕后释放。

        Args:
            fragment_id: 片段ID

        Returns:
            (文档内容, 元数据)
        """
        try:
            from models.metadata_models import MetadataKnowledgeFragment

            with get_db_session() as db:
                fragment = db.query(MetadataKnowledgeFragment).filter(
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

        注意：此方法内部会获取独立的数据库连接，生成完毕后将连接归还。

        Args:
            table_id: 表ID

        Returns:
            [(文档内容, 元数据), ...] 列表
        """
        try:
            # 延迟获取或创建 schema_summary_service
            schema_service = SchemaSummaryService()

            if schema_service:
                # SchemaSummaryService.generate_table_summary 在没有传入 db 时
                # 会在内部自行获取连接，使用完后释放
                documents = schema_service.generate_table_summary(
                    table_id=table_id,
                    include_field_samples=True,
                )

                if documents:
                    return documents
                else:
                    logger.warning(f"Schema摘要服务生成文档失败 table_id={table_id}")
                    return []

            else:
                # 降级：使用简单的表描述（也需要内部获取连接）
                logger.warning("Schema摘要服务不可用，使用简单的表描述")
                return self._generate_simple_table_document(table_id)

        except Exception as e:
            logger.error(f"生成表文档失败 {table_id}: {e}")
            return []

    def _generate_simple_table_document(self, table_id: int) -> List[Tuple[str, Dict]]:
        """生成简单的表文档（降级方案）

        注意：此方法内部获取独立的数据库连接，使用完毕后释放。

        Args:
            table_id: 表ID

        Returns:
            [(文档内容, 元数据), ...] 列表
        """
        try:
            with get_db_session() as db:
                table_repo = MetadataTableRepository(db)
                column_repo = MetadataColumnRepository(db)

                table = table_repo.get_by_id(table_id)
                if not table:
                    return []

                columns = column_repo.get_by_table_id(table_id)
                available_columns = [col for col in columns if col.is_available == 0]

            # 构建基础表结构描述（在 with 块之外进行，不依赖 db session）
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

        注意：此方法内部获取独立的数据库连接，使用完毕后释放。

        Args:
            glossary_id: 术语ID

        Returns:
            (文档内容, 元数据)
        """
        try:
            with get_db_session() as db:
                glossary_repo = GlossaryTermRepository(db)
                glossary = glossary_repo.get_by_id(glossary_id)

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

        注意：此方法内部获取独立的数据库连接，使用完毕后释放。

        Args:
            relation_id: 关联ID

        Returns:
            (文档内容, 元数据)
        """
        try:
            with get_db_session() as db:
                relation_repo = RelationFieldConfigRepository(db)
                relation = relation_repo.get_by_id(relation_id)

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

        注意：此方法内部获取独立的数据库连接，使用完毕后释放。

        Args:
            report_id: 报表ID

        Returns:
            (文档内容, 元数据)
        """
        try:
            with get_db_session() as db:
                fine_report_repo = FineReportRepository(db)
                report = fine_report_repo.get_by_id(report_id)

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

    def _cleanup_orphaned_vectors(self):
        """清理无效资源的向量数据

        注意：此方法在内部获取独立的数据库连接，使用完毕后释放。
        """
        try:
            with get_db_session() as db:
                table_repo = MetadataTableRepository(db)
                glossary_repo = GlossaryTermRepository(db)
                relation_repo = RelationFieldConfigRepository(db)
                fine_report_repo = FineReportRepository(db)

                # 获取当前有效的资源ID列表
                valid_resources = {
                    "table": [t.id for t in table_repo.get_all()],
                    "glossary": [g.id for g in glossary_repo.get_all()],
                    "relation": [r.id for r in relation_repo.get_all()],
                    "fine_report": [r.id for r in fine_report_repo.get_all()]
                }

                # 清理无效的训练记录
                training_repo = TrainingRecordRepository(db)
                deleted_count = training_repo.cleanup_orphaned_records(valid_resources)

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