"""
主题提取服务 - 根据用户主题提取知识
"""

import json
from typing import Dict
from sqlalchemy.orm import Session
from models.metadata_models import MetadataKnowledgeDocument
from repositories.metadata_repository import KnowledgeDocumentRepository
from models.prompt_templates import KnowledgeFragmentationTemplates
from services.llm_service.base_llm_service import BaseLLMService
from utils.logger import logger


class TopicExtractionService:
    """主题提取服务"""

    def __init__(self, db: Session):
        """
        初始化主题提取服务

        Args:
            db: 数据库会话
        """
        self.db = db
        self.doc_repo = KnowledgeDocumentRepository(db)

    def extract_by_topic(
        self,
        document_id: int,
        extraction_theme: str,
        extraction_prompt: str
    ) -> Dict[str, any]:
        """
        根据用户主题提取知识（返回提取的片段，暂存）

        Args:
            document_id: 文档ID
            extraction_theme: 提取主题
            extraction_prompt: 提取逻辑描述

        Returns:
            提取的片段：
            {
                'document_id': 文档ID,
                'fragment': 提取的片段数据,
                'extraction_theme': 提取主题
            }
        """
        try:
            # 获取文档
            document = self.doc_repo.get_by_id(document_id)
            if not document:
                raise ValueError(f"文档不存在: {document_id}")

            logger.info(f"开始从文档 {document_id} 中提取主题: {extraction_theme}")

            # 获取LLM客户端
            llm_client = BaseLLMService()

            # 构建提示词
            prompt = KnowledgeFragmentationTemplates.TOPIC_EXTRACTION_TEMPLATE.format(
                content=document.raw_content,
                extraction_theme=extraction_theme,
                extraction_prompt=extraction_prompt
            )

            # 调用LLM
            logger.info(f"调用LLM提取主题，文档ID: {document_id}, 主题: {extraction_theme}")
            response = llm_client.client.invoke(prompt)

            # 解析响应
            fragment_data = self._parse_extraction_response(response)

            # 构建返回的片段数据（不保存到数据库）
            extracted_fragment = {
                'title': fragment_data.get('title', f'主题提取: {extraction_theme}'),
                'content': fragment_data.get('content', ''),
                'summary': fragment_data.get('summary', ''),
                'generation_method': 'user_extraction',
                'extraction_theme': extraction_theme,
                'extraction_prompt': extraction_prompt,
                'is_modified': False
            }

            logger.info(f"成功提取主题: {extraction_theme}")

            return {
                'document_id': document_id,
                'fragment': extracted_fragment,
                'extraction_theme': extraction_theme
            }

        except Exception as e:
            logger.error(f"主题提取失败: {e}")
            raise

    def _parse_extraction_response(self, response: str) -> Dict[str, str]:
        """
        解析主题提取响应

        Args:
            response: LLM返回的响应字符串

        Returns:
            解析后的片段数据
        """
        try:
            # 尝试提取JSON部分
            start_idx = response.find('{')
            if start_idx == -1:
                # 尝试查找代码块中的JSON
                start_idx = response.find('```json')
                if start_idx != -1:
                    start_idx += 7  # 跳过 ```json
                else:
                    start_idx = response.find('```')
                    if start_idx != -1:
                        start_idx += 3  # 跳过 ```

            if start_idx != -1:
                # 找到JSON开始位置，查找结束位置
                end_idx = response.rfind('}')
                if end_idx != -1 and end_idx > start_idx:
                    json_str = response[start_idx:end_idx + 1]
                    fragment_data = json.loads(json_str)
                    return fragment_data

            # 如果没找到JSON格式，尝试直接解析
            if response.strip().startswith('{'):
                return json.loads(response)

            raise ValueError("无法从响应中提取有效的JSON")

        except json.JSONDecodeError as e:
            logger.error(f"解析主题提取JSON响应失败: {e}")
            logger.debug(f"响应内容: {response}")
            raise ValueError(f"LLM返回的不是有效的JSON格式: {e}")

    def batch_extract_by_topics(
        self,
        document_id: int,
        topics: list
    ) -> Dict[str, any]:
        """
        批量根据多个主题提取知识

        Args:
            document_id: 文档ID
            topics: 主题列表，每个主题包含：
                - extraction_theme: 提取主题
                - extraction_prompt: 提取逻辑描述

        Returns:
            提取的片段列表：
            {
                'document_id': 文档ID,
                'fragments': [提取的片段列表],
                'total_count': 片段数量
            }
        """
        try:
            extracted_fragments = []

            for topic in topics:
                extraction_theme = topic.get('extraction_theme')
                extraction_prompt = topic.get('extraction_prompt')

                if not extraction_theme or not extraction_prompt:
                    logger.warning(f"跳过无效主题: {topic}")
                    continue

                # 提取单个主题
                result = self.extract_by_topic(
                    document_id=document_id,
                    extraction_theme=extraction_theme,
                    extraction_prompt=extraction_prompt
                )

                extracted_fragments.append(result['fragment'])

            logger.info(f"批量提取完成，共提取 {len(extracted_fragments)} 个片段")

            return {
                'document_id': document_id,
                'fragments': extracted_fragments,
                'total_count': len(extracted_fragments)
            }

        except Exception as e:
            logger.error(f"批量主题提取失败: {e}")
            raise
