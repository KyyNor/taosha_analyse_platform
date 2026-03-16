"""
知识库检索工具
基于 Qdrant 向量数据库的知识库检索功能

⚠️ 此模块已废弃，请使用 schema_linking_tool.py 代替。
新工具使用 SchemaLinkingService 提供更准确的表筛选能力。
"""

import json
import warnings
from typing import Optional, List
from langfuse import observe
from utils.logger import logger


def _get_available_table_vector_ids() -> List[str]:
    """获取所有可用表的vector_id列表

    从数据库中查询 is_available=0 的表，并获取其对应的训练记录vector_id

    Returns:
        可用表的vector_id列表
    """
    from models.training_models import TrainingRecord
    from models import MetadataTable
    from models.db_base import SessionLocal

    vector_ids = []
    db = None
    try:
        db = SessionLocal()

        # 查询所有可用表的ID (is_available=0 表示可用)
        available_tables = db.query(MetadataTable).filter(
            MetadataTable.is_available == 0
        ).all()
        table_ids = [table.id for table in available_tables]

        if table_ids:
            # 查询这些表对应的训练记录
            training_records = db.query(TrainingRecord).filter(
                TrainingRecord.resource_type == "table",
                TrainingRecord.resource_id.in_(table_ids),
                TrainingRecord.vector_id != ""
            ).all()

            vector_ids = [record.vector_id for record in training_records]
            logger.info(f"获取到 {len(vector_ids)} 个可用表的vector_id (共 {len(table_ids)} 个可用表)")
        else:
            logger.warning("未找到任何可用表")

    except Exception as e:
        logger.error(f"获取可用表vector_ids失败: {e}", exc_info=True)
    finally:
        if db:
            db.close()

    return vector_ids


@observe(name="search_knowledge_base")
def search_knowledge_base(
    query: str,
    top_k: int = 5,
    search_mode: str = "hybrid",
    score_threshold: Optional[float] = None
) -> str:
    """
    ⚠️ 此函数已废弃，请使用 schema_linking_retrieve 代替。
    新工具使用 SchemaLinkingService 提供更准确的表筛选能力（两阶段检索 + 内置reranker）。

    在知识库中检索相关文档和知识，知识库中包括表结构、业务术语、关联关系等信息。

    Args:
        query: 查询文本。描述你想要查找的内容。

        top_k: 每类返回结果数量，默认 5 条。建议范围 3-10。
               会分别返回最多 top_k 个表结构和 top_k 个其他文档。

        search_mode: 搜索模式，可选值:
                    - "vector_only": 纯向量语义搜索，适合概念理解和语义相似
                    - "fulltext_only": 纯全文关键词搜索，适合精确匹配
                    - "hybrid": 混合搜索（推荐），结合语义和关键词

        score_threshold: 分数阈值，仅返回分数高于此值的结果。设置为 None 则不过滤。

    Returns:
        JSON 格式的检索结果字符串，包含以下字段:
        - success: bool, 是否成功
        - query: str, 原始查询
        - search_mode: str, 使用的搜索模式
        - result_count: int, 返回的总结果数量
        - table_count: int, 表结构结果数量
        - other_count: int, 其他文档结果数量
        - results: list, 检索结果列表，每个结果包含:
            - id: str, 文档ID
            - content: str, 文档内容
            - score: float, 相似度分数
            - rerank_score: float, 重排序分数
            - resource_type: str, 资源类型（table/glossary/relation/other）
            - metadata: dict, 元数据（如来源、标签等）
        - error: str, 错误信息（仅在失败时）

    Examples:
        # 语义搜索 - 同时返回表结构和业务知识
        search_knowledge_base("什么是用户留存率", top_k=5)

        # 精确关键词搜索
        search_knowledge_base("DAU MAU", search_mode="fulltext_only")

        # 混合搜索并设置分数阈值
        search_knowledge_base("风控规则配置", search_mode="hybrid", score_threshold=0.6)
    """
    logger.info(f"知识库检索: {query[:50]}... (mode={search_mode}, top_k={top_k})")

    try:
        # 延迟导入，避免循环依赖和启动时的初始化问题
        from services.vector_store.qdrant_vector_store import qdrant_vector_store
        from qdrant_client.http.models import Filter, FieldCondition, MatchValue

        # 步骤1：获取可用表的vector_ids
        allowed_table_ids = _get_available_table_vector_ids()
        if not allowed_table_ids:
            logger.warning("未找到可用表的vector_id，将不过滤表结构")

        # 步骤2：分离检索 - 先检索表结构
        logger.info("执行表结构检索...")
        table_results = qdrant_vector_store.search(
            query=query,
            top_k=top_k,
            search_mode=search_mode,
            score_threshold=score_threshold,
            filters=Filter(must=[
                FieldCondition(key="resource_type", match=MatchValue(value="table"))
            ]),
            allowed_ids=allowed_table_ids  # 只返回可用表
        )
        table_count = len(table_results)
        logger.info(f"检索到 {table_count} 个表结构结果")

        # 步骤3：检索其他文档（术语、关联关系等）
        logger.info("执行其他文档检索...")
        other_results = qdrant_vector_store.search(
            query=query,
            top_k=top_k,
            search_mode=search_mode,
            score_threshold=score_threshold,
            filters=Filter(must_not=[
                FieldCondition(key="resource_type", match=MatchValue(value="table"))
            ])
        )
        other_count = len(other_results)
        logger.info(f"检索到 {other_count} 个其他文档结果")

        # 步骤4：合并结果（表在前，其他在后）
        all_results = table_results + other_results

        # 步骤5：格式化结果
        formatted_results = []
        for item in all_results:
            metadata = item.get("metadata", {})
            resource_type = metadata.get("resource_type", "unknown")

            formatted_results.append({
                "id": item.get("id", ""),
                "content": item.get("content", ""),
                "score": round(item.get("score", 0.0), 4),
                "rerank_score": round(item.get("rerank_score", 0.0), 4),
                "resource_type": resource_type,
                "metadata": {
                    k: v for k, v in metadata.items()
                    if k not in ["content", "id"]  # 排除重复字段
                }
            })

        logger.info(f"知识库检索成功，返回 {len(formatted_results)} 条结果 "
                   f"(表结构: {table_count}, 其他文档: {other_count})")

        return json.dumps({
            "success": True,
            "query": query,
            "search_mode": search_mode,
            "result_count": len(formatted_results),
            "table_count": table_count,
            "other_count": other_count,
            "results": formatted_results
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"知识库检索失败: {e}", exc_info=True)
        return json.dumps({
            "success": False,
            "query": query,
            "error": str(e),
            "result_count": 0,
            "table_count": 0,
            "other_count": 0,
            "results": []
        }, ensure_ascii=False)
