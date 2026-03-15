"""
知识片段生成服务 - 基于LLM生成知识片段
"""

import json
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from models.metadata_models import MetadataKnowledgeDocument, MetadataKnowledgeFragment
from repositories.metadata_repository import KnowledgeDocumentRepository, KnowledgeFragmentRepository
from models.prompt_templates import KnowledgeFragmentationTemplates
from services.llm_service.llm_manager import get_llm_client
from utils.logger import logger


class FragmentGenerationService:
    """知识片段生成服务"""

    # 最大候选片段数（暂存）
    MAX_CANDIDATE_FRAGMENTS = 20

    # 默认生成的片段数
    DEFAULT_FRAGMENT_COUNT = 5

    def __init__(self, db: Session):
        """
        初始化片段生成服务

        Args:
            db: 数据库会话
        """
        self.db = db
        self.doc_repo = KnowledgeDocumentRepository(db)
        self.frag_repo = KnowledgeFragmentRepository(db)

    def generate_fragments(
        self,
        document_id: int,
        fragment_count: int = DEFAULT_FRAGMENT_COUNT
    ) -> Dict[str, Any]:
        """
        生成N个候选片段（暂存，不直接入库）

        Args:
            document_id: 文档ID
            fragment_count: 生成的片段数量

        Returns:
            包含候选片段的字典：
            {
                'document_id': 文档ID,
                'fragments': [候选片段列表],
                'total_count': 片段数量
            }
        """
        try:
            # 验证输入
            if fragment_count < 1 or fragment_count > self.MAX_CANDIDATE_FRAGMENTS:
                raise ValueError(f"片段数量必须在1-{self.MAX_CANDIDATE_FRAGMENTS}之间")

            # 获取文档
            document = self.doc_repo.get_by_id(document_id)
            if not document:
                raise ValueError(f"文档不存在: {document_id}")

            logger.info(f"开始为文档 {document_id} 生成 {fragment_count} 个片段")

            # 获取LLM客户端
            llm_client = get_llm_client()

            # 构建提示词
            content_type = "SQL脚本" if document.source_type == "sql" else "文本内容"
            prompt = KnowledgeFragmentationTemplates.FRAGMENT_GENERATION_TEMPLATE.format(
                content=document.raw_content,
                fragment_count=fragment_count,
                content_type=content_type
            )

            # 调用LLM
            logger.info(f"调用LLM生成片段，文档ID: {document_id}")
            response = llm_client.generate(prompt)

            # 解析响应
            fragments_data = self._parse_llm_response(response)

            # 验证片段数量
            if len(fragments_data) != fragment_count:
                logger.warning(f"LLM返回的片段数量({len(fragments_data)})与请求的不一致({fragment_count})")

            # 转换为候选片段格式（不保存到数据库）
            candidate_fragments = []
            for frag_data in fragments_data:
                candidate_fragments.append({
                    'title': frag_data.get('title', '未命名片段'),
                    'content': frag_data.get('content', ''),
                    'summary': frag_data.get('summary', ''),
                    'generation_method': 'auto',
                    'extraction_theme': None,
                    'is_modified': False
                })

            logger.info(f"成功生成 {len(candidate_fragments)} 个候选片段")

            return {
                'document_id': document_id,
                'fragments': candidate_fragments,
                'total_count': len(candidate_fragments)
            }

        except Exception as e:
            logger.error(f"生成片段失败: {e}")
            raise

    def save_selected_fragments(
        self,
        document_id: int,
        selected_fragments: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        保存用户选中的片段到数据库

        前端传递完整的片段数据列表，直接保存到数据库。
        不区分编辑前编辑后，所有片段以前端传递的数据为准。

        Args:
            document_id: 文档ID
            selected_fragments: 要保存的片段列表（完整数据），每个片段包含：
                - title: 标题（必需）
                - content: 内容（必需）
                - summary: 摘要（可选）
                - generation_method: 生成方式（auto/user_extraction/manual）
                - extraction_theme: 提取主题（可选）
                - is_modified: 是否被修改

        Returns:
            保存结果：
            {
                'saved_fragment_ids': [片段ID列表],
                'saved_count': 保存数量,
                'document_id': 文档ID
            }
        """
        try:
            # 验证输入
            if not selected_fragments:
                raise ValueError("没有选中任何片段")

            # 获取文档
            document = self.doc_repo.get_by_id(document_id)
            if not document:
                raise ValueError(f"文档不存在: {document_id}")

            logger.info(f"开始保存 {len(selected_fragments)} 个片段到文档 {document_id}")

            # 准备批量插入的数据
            fragments_to_create = []
            for frag_data in selected_fragments:
                fragments_to_create.append({
                    'document_id': document_id,
                    'title': frag_data.get('title', '未命名片段'),
                    'content': frag_data.get('content', ''),
                    'summary': frag_data.get('summary', ''),
                    'generation_method': frag_data.get('generation_method', 'auto'),
                    'extraction_theme': frag_data.get('extraction_theme'),
                    'extraction_prompt': frag_data.get('extraction_prompt'),
                    'is_modified': frag_data.get('is_modified', False)
                })

            # 批量创建片段
            created_fragments = self.frag_repo.bulk_create(fragments_to_create)

            # 更新文档的片段数量
            self.doc_repo.update_fragment_count(document_id, len(created_fragments))

            # 创建或更新TrainingRecord（用于向量训练）
            self._create_training_records(created_fragments)

            fragment_ids = [frag.id for frag in created_fragments]

            logger.info(f"成功保存 {len(created_fragments)} 个片段，IDs: {fragment_ids}")

            return {
                'saved_fragment_ids': fragment_ids,
                'saved_count': len(created_fragments),
                'document_id': document_id
            }

        except Exception as e:
            logger.error(f"保存片段失败: {e}")
            self.db.rollback()
            raise

    def _parse_llm_response(self, response: str) -> List[Dict[str, str]]:
        """
        解析LLM JSON响应

        Args:
            response: LLM返回的响应字符串

        Returns:
            解析后的片段列表
        """
        try:
            # 尝试直接解析JSON
            if response.strip().startswith('['):
                fragments = json.loads(response)
                return fragments
            elif response.strip().startswith('{'):
                # 单个片段
                fragment = json.loads(response)
                return [fragment]
            else:
                # 尝试提取JSON部分
                start_idx = response.find('[')
                if start_idx == -1:
                    start_idx = response.find('{')

                if start_idx != -1:
                    # 尝试找到匹配的结束符
                    if response[start_idx] == '[':
                        end_idx = response.rfind(']') + 1
                    else:
                        end_idx = response.rfind('}') + 1

                    json_str = response[start_idx:end_idx]
                    fragments = json.loads(json_str)

                    if isinstance(fragments, list):
                        return fragments
                    elif isinstance(fragments, dict):
                        return [fragments]

                raise ValueError("无法从响应中提取有效的JSON")

        except json.JSONDecodeError as e:
            logger.error(f"解析LLM JSON响应失败: {e}")
            logger.debug(f"响应内容: {response}")
            raise ValueError(f"LLM返回的不是有效的JSON格式: {e}")

    def _create_training_records(self, fragments: List[MetadataKnowledgeFragment]):
        """
        为片段创建TrainingRecord（用于向量训练）

        Args:
            fragments: 片段列表
        """
        try:
            from repositories.training_repository import TrainingRecordRepository
            from datetime import datetime

            training_repo = TrainingRecordRepository(self.db)

            for fragment in fragments:
                # 检查是否已存在训练记录
                existing = training_repo.get_by_resource_type_and_id(
                    resource_type="knowledge_fragment",
                    resource_id=fragment.id
                )

                if existing:
                    # 更新为pending状态
                    training_repo.update(fragment.id, training_status="pending")
                    logger.debug(f"更新片段 {fragment.id} 的训练记录为pending")
                else:
                    # 创建新的训练记录
                    training_repo.create(
                        resource_type="knowledge_fragment",
                        resource_id=fragment.id,
                        training_status="pending",
                        last_modified_at=fragment.updated_at
                    )
                    logger.debug(f"为片段 {fragment.id} 创建训练记录")

        except Exception as e:
            logger.error(f"创建训练记录失败: {e}")
            # 不影响主流程，继续执行

    def update_fragment(
        self,
        fragment_id: int,
        title: Optional[str] = None,
        content: Optional[str] = None,
        summary: Optional[str] = None
    ) -> MetadataKnowledgeFragment:
        """
        更新片段内容

        Args:
            fragment_id: 片段ID
            title: 新标题
            content: 新内容
            summary: 新摘要

        Returns:
            更新后的片段
        """
        try:
            # 获取片段
            fragment = self.frag_repo.get_by_id(fragment_id)
            if not fragment:
                raise ValueError(f"片段不存在: {fragment_id}")

            # 构建更新数据
            update_data = {}
            if title is not None:
                update_data['title'] = title
            if content is not None:
                update_data['content'] = content
            if summary is not None:
                update_data['summary'] = summary

            # 标记为已修改
            update_data['is_modified'] = True

            # 更新片段
            updated_fragment = self.frag_repo.update(fragment_id, **update_data)

            # 更新训练记录为pending（需要重新训练）
            self._update_training_record(fragment_id)

            logger.info(f"成功更新片段: {fragment_id}")

            return updated_fragment

        except Exception as e:
            logger.error(f"更新片段失败: {e}")
            raise

    def _update_training_record(self, fragment_id: int):
        """
        更新片段的训练记录状态为pending

        Args:
            fragment_id: 片段ID
        """
        try:
            from repositories.training_repository import TrainingRecordRepository

            training_repo = TrainingRecordRepository(self.db)
            training_repo.update(fragment_id, training_status="pending")

        except Exception as e:
            logger.error(f"更新训练记录失败: {e}")
