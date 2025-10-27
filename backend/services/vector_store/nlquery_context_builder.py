"""
NL2SQL 专用的上下文构建器 - 业务级别的检索和上下文组织
"""

from typing import List, Dict, Optional

from qdrant_client.http.models import MatchAny, Filter, MatchValue, FieldCondition

from services.metadata_service.metadata_service import (
    get_metadata_service,
    get_glossary_service,
    get_relation_field_config_service
)
from services.vector_store.qdrant_vector_store import qdrant_vector_store
from utils.logger import logger


class NLQueryContextBuilder:
    """NL2SQL 专用的上下文构建器

    提供多种业务场景的检索方法，将向量库搜索结果组织成适合 LLM 的提示词格式
    """

    def __init__(self,
                 metadata_service=None,
                 glossary_service=None,
                 relation_config_service=None):
        """初始化上下文构建器

        Args:
            metadata_service: 元数据服务（可选，未提供则自动获取）
            glossary_service: 术语服务（可选，未提供则自动获取）
            relation_config_service: 关联配置服务（可选，未提供则自动获取）
        """
        self.vector_store = qdrant_vector_store

        # 如果未提供服务，则获取全局实例
        self.metadata_service = metadata_service or get_metadata_service()
        self.glossary_service = glossary_service or get_glossary_service()
        self.relation_config_service = relation_config_service or get_relation_field_config_service()

        logger.info("NLQuery Context Builder 初始化完成，使用全局 VectorStore 实例")

    def retrieve_by_semantic_search(self, user_input: str, top_k: int = 10, allowed_vector_ids: List[str] = None) -> str:
        """纯向量检索 - 根据语义相似度检索

        使用场景：一般性的自然语言查询，直接根据用户输入的语义相似度检索

        Args:
            user_input: 用户的自然语言输入
            top_k: 返回结果数量
            allowed_vector_ids: 限制检索的vector_id列表（基于表选择的精准过滤）

        Returns:
            格式化的提示词上下文（包含表、字段、术语等信息）
        """
        logger.info(f"执行纯向量检索: {user_input[:50]}... (过滤IDs数: {len(allowed_vector_ids) if allowed_vector_ids else 0})")

        try:
            # 1. 获取基础术语上下文
            basic_terms_context = self.get_basic_terms_context()
            
            # 2. 执行向量搜索 先检索表
            table_search_results = self.vector_store.search(
                user_input,
                top_k=top_k,
                filters=Filter(must=FieldCondition(key="resource_type", match=MatchValue(value="table"))),
                allowed_ids=allowed_vector_ids,
                score_threshold=0.6,
            )

            # 再检索其他
            other_search_results = self.vector_store.search(
                user_input,
                top_k=top_k,
                filters=Filter(must_not=FieldCondition(key="resource_type", match=MatchValue(value="table"))),
                score_threshold=0.6,
            )

            # 3. 分类组织结果
            table_docs = []
            glossary_docs = []
            other_docs = []

            for result in table_search_results + other_search_results:
                metadata = result.get("metadata", {})
                doc_type = metadata.get("resource_type", "unknown")

                if doc_type == "table":
                    table_docs.append(result)
                elif doc_type == "glossary":
                    glossary_docs.append(result)
                else:
                    other_docs.append(result)

            # 4. 格式化上下文
            context_parts = []
            
            # 先添加基础术语上下文
            if basic_terms_context:
                context_parts.append(basic_terms_context)

            if table_docs:
                context_parts.append(self._format_table_section(table_docs))

            if glossary_docs:
                context_parts.append(self._format_glossary_section(glossary_docs))

            if other_docs:
                context_parts.append(self._format_other_section(other_docs))

            context = "\n\n".join(context_parts)
            logger.info(context)
            logger.info(f"向量检索完成，返回 {len(table_search_results + other_search_results)} 个结果")
            return context

        except Exception as e:
            logger.error(f"纯向量检索失败: {e}")
            raise RuntimeError(f"上下文检索失败: {e}")


    # ========== 内部格式化方法 ==========

    def _format_table_section(self, docs: List[Dict]) -> str:
        """格式化表信息部分"""
        lines = ["可用的表结构："]
        for doc in docs:
            content = doc.get("content", "")
            lines.append(f"  {content}")
        return "\n".join(lines)

    def _format_glossary_section(self, docs: List[Dict]) -> str:
        """格式化术语部分"""
        lines = ["可用的业务术语："]
        for doc in docs:
            content = doc.get("content", "")
            lines.append(f"  {content}")
        return "\n".join(lines)

    def _format_other_section(self, docs: List[Dict]) -> str:
        """格式化其他信息部分"""
        lines = ["相关信息："]
        for doc in docs:
            content = doc.get("content", "")
            lines.append(f"  {content}")
        return "\n".join(lines)

    def _format_complete_table(self, table_info: Dict) -> str:
        """格式化单个表的完整信息"""
        lines = []

        table_name = table_info.get("name", "")
        table_comment = table_info.get("comment", "")

        # 表头
        lines.append(f"表名: {table_name}")
        if table_comment:
            lines.append(f"描述: {table_comment}")

        # 字段信息
        columns = table_info.get("columns", [])
        if columns:
            lines.append("字段:")
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

                lines.append(col_line)

        return "\n".join(lines)

    def _format_relation_fields(self, fields: List[Dict], relation_id: str) -> str:
        """格式化关联字段信息"""
        lines = [f"字段关联配置 (关联ID: {relation_id}):"]

        for field in fields:
            table_name = field.get("table_name", "")
            col_name = field.get("column_name", "")
            col_type = field.get("type", "")
            col_comment = field.get("comment", "")

            line = f"  - {table_name}.{col_name} ({col_type})"
            if col_comment:
                line += f": {col_comment}"

            lines.append(line)

        return "\n".join(lines)

    def _format_search_results(self, results: List[Dict]) -> str:
        """格式化向量搜索结果"""
        lines = ["检索到的相关信息:"]

        for result in results:
            content = result.get("content", "")
            score = result.get("score", 0)
            lines.append(f"  - {content} (相似度: {score:.2f})")

        return "\n".join(lines)

    def _get_fields_by_relation_id(self, relation_id: str) -> List[Dict]:
        """获取指定关联ID的所有字段

        Returns:
            字段列表，每个字段包含：
            {
                "table_name": "...",
                "column_name": "...",
                "type": "...",
                "comment": "..."
            }
        """
        fields = []

        try:
            # 获取所有表
            all_tables = self.metadata_service.get_available_tables()

            # 遍历查找关联ID匹配的字段
            for table in all_tables:
                table_name = table.get("name", "")
                columns = table.get("columns", [])

                for col in columns:
                    if col.get("relation_id") == relation_id:
                        fields.append({
                            "table_name": table_name,
                            "column_name": col.get("name", ""),
                            "type": col.get("business_type") or col.get("type", ""),
                            "comment": col.get("comment", "")
                        })

            logger.debug(f"找到 {len(fields)} 个关联ID为 {relation_id} 的字段")

        except Exception as e:
            logger.error(f"获取关联字段失败: {e}")

        return fields

    def _prioritize_by_relation(self,
                               results: List[Dict],
                               relation_fields: List[Dict]) -> List[Dict]:
        """根据关联字段重排检索结果

        将包含关联字段表名的结果优先排列

        Args:
            results: 搜索结果
            relation_fields: 关联字段列表

        Returns:
            重排后的结果
        """
        relation_table_names = {f.get("table_name") for f in relation_fields}

        # 分类：属于关联表的和其他的
        related_results = []
        other_results = []

        for result in results:
            metadata = result.get("metadata", {})
            table_name = metadata.get("table_name", "")

            if table_name in relation_table_names:
                related_results.append(result)
            else:
                other_results.append(result)

        # 关联字段优先
        return related_results + other_results

    def get_basic_terms_context(self) -> str:
        """获取基础术语的上下文"""
        try:
            basic_terms = self.glossary_service.get_basic_terms()
            
            if not basic_terms:
                return ""
            
            context_parts = ["基础业务术语："]
            for term in basic_terms:
                term_name = term.get("name", "")
                term_type = term.get("type", "")
                content = term.get("content", {})
                
                term_desc = f"  - {term_name} ({term_type})"
                
                if term_type == "concept_explanation":
                    term_desc += f": {content.get('explanation', '')}"
                elif term_type == "sql_qa":
                    term_desc += f" - 问题: {content.get('question', '')}, 答案: {content.get('answer', '')}"
                elif term_type == "dictionary_conversion":
                    term_desc += f" - 转换规则: {content.get('conversion_rule', '')}"
                
                context_parts.append(term_desc)
            
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"获取基础术语上下文失败: {e}")
            return ""
