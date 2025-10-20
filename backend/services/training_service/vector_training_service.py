"""
向量数据库训练服务 - 负责将元数据训练到向量数据库中
"""

import json
import time
from typing import List, Dict, Any, Optional
from datetime import datetime

from sqlalchemy.orm import Session

from utils.logger import logger
from repositories.training_repository import (
    TrainingSessionRepository,
    TrainingMetricsRepository
)
from services.vector_store import VectorStoreFactory
from services.metadata_service.metadata_service import (
    get_metadata_service,
    get_glossary_service,
    get_relation_field_config_service
)


class VectorTrainingService:
    """向量数据库训练服务

    负责将元数据（表结构、术语表、关联配置）训练到向量数据库中，
    并记录训练过程和统计信息到数据库。
    """

    def __init__(self, db: Session):
        """初始化向量训练服务

        Args:
            db: 数据库会话
        """
        self.db = db
        self.session_repo = TrainingSessionRepository(db)
        self.metrics_repo = TrainingMetricsRepository(db)

        # 初始化元数据服务
        self.metadata_service = get_metadata_service()
        self.glossary_service = get_glossary_service()
        self.relation_service = get_relation_field_config_service()

        # 使用全局向量存储实例
        try:
            from services.vector_store.vector_store_factory import get_vector_store
            self.vector_store = get_vector_store()
            logger.info("向量存储初始化成功，使用全局实例")
        except Exception as e:
            logger.error(f"向量存储初始化失败: {e}")
            raise

    def train_vector_database(self, session_name: str = "向量数据库初始化训练") -> Dict[str, Any]:
        """训练向量数据库

        Args:
            session_name: 训练会话名称

        Returns:
            训练结果字典
        """
        try:
            logger.info(f"开始向量数据库训练: {session_name}")
            start_time = time.time()

            # 创建训练会话
            session = self.session_repo.create(
                session_name=session_name,
                session_type="auto",
                status="running",
                notes="向量数据库元数据训练",
                created_by="system"
            )
            session_id = session.id

            # 更新开始时间
            self.session_repo.update(session_id, started_at=datetime.now())

            # 获取所有元数据
            documents = []
            metadatas = []

            # 1. 获取表结构信息
            table_docs, table_metas = self._get_table_documents()
            documents.extend(table_docs)
            metadatas.extend(table_metas)

            # 2. 获取术语表信息
            glossary_docs, glossary_metas = self._get_glossary_documents()
            documents.extend(glossary_docs)
            metadatas.extend(glossary_metas)

            # 3. 获取关联配置信息
            relation_docs, relation_metas = self._get_relation_documents()
            documents.extend(relation_docs)
            metadatas.extend(relation_metas)

            # 清空现有向量数据
            try:
                # self.vector_store.clear()
                logger.info("已清空现有向量数据 (todo)")
            except Exception as e:
                logger.warning(f"清空向量数据失败: {e}")

            # 添加到向量数据库
            success_count = 0
            failed_count = 0

            if documents:
                try:
                    ids = self.vector_store.add(documents=documents, metadatas=metadatas)
                    success_count = len(ids)
                    logger.info(f"成功添加 {success_count} 个文档到向量数据库")
                except Exception as e:
                    logger.error(f"添加文档到向量数据库失败: {e}")
                    failed_count = len(documents)

            # 计算训练时间
            training_time = time.time() - start_time

            # 记录训练指标
            self._record_training_metrics(session_id, {
                "total_documents": len(documents),
                "table_documents": len(table_docs),
                "glossary_documents": len(glossary_docs),
                "relation_documents": len(relation_docs),
                "success_count": success_count,
                "failed_count": failed_count,
                "training_time": training_time
            })

            # 更新训练会话状态
            success_rate = (success_count / len(documents)) if documents else 0.0
            self.session_repo.complete_session(
                session_id=session_id,
                success_rate=success_rate,
                avg_confidence=1.0,  # 向量训练的置信度设为1.0
                training_time=training_time
            )

            result = {
                "success": failed_count == 0,
                "session_id": session_id,
                "total_documents": len(documents),
                "success_count": success_count,
                "failed_count": failed_count,
                "training_time": training_time,
                "success_rate": success_rate
            }

            logger.info(f"向量数据库训练完成: {result}")
            return result

        except Exception as e:
            logger.error(f"向量数据库训练失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "session_id": session_id if 'session_id' in locals() else None
            }

    def _get_table_documents(self) -> tuple[List[str], List[Dict]]:
        """获取表结构文档

        Returns:
            (文档内容列表, 元数据列表)
        """
        documents = []
        metadatas = []

        try:
            tables = self.metadata_service.get_available_tables()

            for table in tables:
                table_name = table.get("name", "")
                table_comment = table.get("comment", "")
                columns = table.get("columns", [])

                # 构建表结构描述
                doc_lines = [f"表名: {table_name}"]
                if table_comment:
                    doc_lines.append(f"表描述: {table_comment}")

                doc_lines.append("字段信息:")
                for col in columns:
                    col_name = col.get("name", "")
                    col_type = col.get("business_type") or col.get("type", "")
                    col_comment = col.get("comment", "")
                    relation_id = col.get("relation_id", "")

                    col_line = f"  - {col_name} ({col_type})"
                    if col_comment:
                        col_line += f": {col_comment}"
                    if relation_id:
                        col_line += f" [关联ID: {relation_id}]"

                    doc_lines.append(col_line)

                document = "\n".join(doc_lines)
                documents.append(document)

                # 构建元数据
                metadata = {
                    "type": "table",
                    "table_name": table_name,
                    "column_count": len(columns),
                    "source": "metadata_service"
                }
                metadatas.append(metadata)

            logger.info(f"获取到 {len(tables)} 个表的文档")

        except Exception as e:
            logger.error(f"获取表文档失败: {e}")

        return documents, metadatas

    def _get_glossary_documents(self) -> tuple[List[str], List[Dict]]:
        """获取术语表文档

        Returns:
            (文档内容列表, 元数据列表)
        """
        documents = []
        metadatas = []

        try:
            glossaries = self.glossary_service.get_terms()

            for glossary in glossaries:
                term = glossary.get("term", "")
                definition = glossary.get("definition", "")
                glossary_type = glossary.get("type", "")
                category = glossary.get("category", "")

                # 构建术语描述
                doc_lines = [f"术语: {term}"]
                doc_lines.append(f"定义: {definition}")
                doc_lines.append(f"类型: {glossary_type}")
                if category:
                    doc_lines.append(f"分类: {category}")

                document = "\n".join(doc_lines)
                documents.append(document)

                # 构建元数据
                metadata = {
                    "type": "glossary",
                    "term": term,
                    "glossary_type": glossary_type,
                    "category": category,
                    "source": "glossary_service"
                }
                metadatas.append(metadata)

            logger.info(f"获取到 {len(glossaries)} 个术语的文档")

        except Exception as e:
            logger.error(f"获取术语文档失败: {e}")

        return documents, metadatas

    def _get_relation_documents(self) -> tuple[List[str], List[Dict]]:
        """获取关联配置文档

        Returns:
            (文档内容列表, 元数据列表)
        """
        documents = []
        metadatas = []

        try:
            relations = self.relation_service.get_all_relation_configs()

            for relation in relations:
                relation_id = relation.get("relation_id", "")
                family_name = relation.get("family_name", "")
                sub_family_name = relation.get("sub_family_name", "")
                description = relation.get("description", "")
                fields = relation.get("fields", [])

                # 构建关联配置描述
                doc_lines = [f"关联ID: {relation_id}"]
                doc_lines.append(f"关系家族: {family_name}")
                if sub_family_name:
                    doc_lines.append(f"子家族: {sub_family_name}")
                if description:
                    doc_lines.append(f"描述: {description}")

                doc_lines.append("包含字段:")
                for field in fields:
                    table_name = field.get("table_name", "")
                    column_name = field.get("column_name", "")
                    col_comment = field.get("comment", "")

                    field_line = f"  - {table_name}.{column_name}"
                    if col_comment:
                        field_line += f": {col_comment}"

                    doc_lines.append(field_line)

                document = "\n".join(doc_lines)
                documents.append(document)

                # 构建元数据
                metadata = {
                    "type": "relation",
                    "relation_id": relation_id,
                    "family_name": family_name,
                    "sub_family_name": sub_family_name,
                    "field_count": len(fields),
                    "source": "relation_service"
                }
                metadatas.append(metadata)

            logger.info(f"获取到 {len(relations)} 个关联配置的文档")

        except Exception as e:
            logger.error(f"获取关联配置文档失败: {e}")

        return documents, metadatas

    def _record_training_metrics(self, session_id: int, metrics: Dict[str, Any]):
        """记录训练指标

        Args:
            session_id: 训练会话ID
            metrics: 指标数据
        """
        try:
            # 记录各种指标
            self.metrics_repo.add_metric(
                session_id=session_id,
                metric_name="total_documents",
                metric_value=metrics["total_documents"],
                metric_type="training",
                description="训练的文档总数"
            )

            self.metrics_repo.add_metric(
                session_id=session_id,
                metric_name="table_documents",
                metric_value=metrics["table_documents"],
                metric_type="training",
                description="表结构文档数量"
            )

            self.metrics_repo.add_metric(
                session_id=session_id,
                metric_name="glossary_documents",
                metric_value=metrics["glossary_documents"],
                metric_type="training",
                description="术语表文档数量"
            )

            self.metrics_repo.add_metric(
                session_id=session_id,
                metric_name="relation_documents",
                metric_value=metrics["relation_documents"],
                metric_type="training",
                description="关联配置文档数量"
            )

            self.metrics_repo.add_metric(
                session_id=session_id,
                metric_name="training_time_seconds",
                metric_value=metrics["training_time"],
                metric_type="performance",
                description="训练耗时（秒）"
            )

            self.metrics_repo.add_metric(
                session_id=session_id,
                metric_name="success_rate",
                metric_value=(metrics["success_count"] / metrics["total_documents"]) if metrics["total_documents"] > 0 else 0.0,
                metric_type="quality",
                description="训练成功率"
            )

            logger.info(f"训练指标已记录到会话 {session_id}")

        except Exception as e:
            logger.error(f"记录训练指标失败: {e}")

    def get_training_status(self) -> Dict[str, Any]:
        """获取训练状态信息

        Returns:
            训练状态字典
        """
        try:
            # 获取最近的训练会话
            recent_sessions = self.session_repo.get_recent_sessions(days=7, limit=5)

            # 获取向量数据库文档数量
            vector_count = 0
            try:
                vector_count = self.vector_store.count()
            except Exception as e:
                logger.warning(f"获取向量数据库文档数量失败: {e}")

            return {
                "recent_sessions": [
                    {
                        "id": s.id,
                        "name": s.session_name,
                        "status": s.status,
                        "success_rate": s.success_rate,
                        "created_at": s.created_at.isoformat()
                    }
                    for s in recent_sessions
                ],
                "vector_database": {
                    "document_count": vector_count
                }
            }

        except Exception as e:
            logger.error(f"获取训练状态失败: {e}")
            return {"error": str(e)}