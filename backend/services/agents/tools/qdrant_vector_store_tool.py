"""
知识库检索工具
基于 Qdrant 向量数据库的知识库检索功能
"""

import json
from typing import Optional, List
from langfuse import observe
from utils.logger import logger


@observe(name="search_knowledge_base")
def search_knowledge_base(
    query: str,
    top_k: int = 5,
    search_mode: str = "hybrid",
    score_threshold: Optional[float] = None
) -> str:
    """
    在知识库中检索相关文档和知识

    Args:
        query: 查询文本。描述你想要查找的内容，可以是：
               - 关键词: "用户活跃度"
               - 问题: "如何计算转化率？"
               - 概念: "风控模型的评估指标"

        top_k: 返回结果数量，默认 5 条。建议范围 3-10

        search_mode: 搜索模式，可选值:
                    - "vector_only": 纯向量语义搜索，适合概念理解和语义相似
                    - "fulltext_only": 纯全文关键词搜索，适合精确匹配
                    - "hybrid": 混合搜索（推荐），结合语义和关键词

        score_threshold: 分数阈值，仅返回分数高于此值的结果。
                        设置为 None 则不过滤。建议值: 0.5-0.8

    Returns:
        JSON 格式的检索结果字符串，包含以下字段:
        - success: bool, 是否成功
        - query: str, 原始查询
        - result_count: int, 返回的结果数量
        - results: list, 检索结果列表，每个结果包含:
            - id: str, 文档ID
            - content: str, 文档内容
            - score: float, 相似度分数
            - rerank_score: float, 重排序分数
            - metadata: dict, 元数据（如来源、标签等）
        - error: str, 错误信息（仅在失败时）

    Examples:
        # 语义搜索
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

        # 执行检索
        results = qdrant_vector_store.search(
            query=query,
            top_k=top_k,
            search_mode=search_mode,
            score_threshold=score_threshold
        )

        # 格式化结果
        formatted_results = []
        for item in results:
            formatted_results.append({
                "id": item.get("id", ""),
                "content": item.get("content", ""),
                "score": round(item.get("score", 0.0), 4),
                "rerank_score": round(item.get("rerank_score", 0.0), 4),
                "metadata": {
                    k: v for k, v in item.get("metadata", {}).items()
                    if k not in ["content", "id"]  # 排除重复字段
                }
            })

        logger.info(f"知识库检索成功，返回 {len(formatted_results)} 条结果")

        return json.dumps({
            "success": True,
            "query": query,
            "search_mode": search_mode,
            "result_count": len(formatted_results),
            "results": formatted_results
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"知识库检索失败: {e}")
        return json.dumps({
            "success": False,
            "query": query,
            "error": str(e),
            "result_count": 0,
            "results": []
        }, ensure_ascii=False)


@observe(name="get_knowledge_base_stats")
def get_knowledge_base_stats() -> str:
    """
    获取知识库统计信息

    Returns:
        JSON 格式的统计信息，包含:
        - success: bool, 是否成功
        - document_count: int, 文档总数
        - collection_name: str, 集合名称
        - health: bool, 健康状态
    """
    logger.info("获取知识库统计信息")

    try:
        from services.vector_store.qdrant_vector_store import qdrant_vector_store

        count = qdrant_vector_store.count()
        health = qdrant_vector_store.health_check()

        return json.dumps({
            "success": True,
            "document_count": count,
            "collection_name": qdrant_vector_store.collection_name,
            "health": health
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"获取知识库统计信息失败: {e}")
        return json.dumps({
            "success": False,
            "error": str(e)
        }, ensure_ascii=False)


@observe(name="search_similar_documents")
def search_similar_documents(
    document_id: str,
    top_k: int = 5
) -> str:
    """
    根据文档ID查找相似文档

    Args:
        document_id: 源文档的ID
        top_k: 返回结果数量

    Returns:
        JSON 格式的相似文档列表
    """
    logger.info(f"查找相似文档: {document_id}")

    try:
        from services.vector_store.qdrant_vector_store import qdrant_vector_store

        # 先获取源文档内容
        # 使用ID过滤获取源文档
        from qdrant_client.http.models import FieldCondition, MatchAny, Filter

        # 获取源文档的内容作为查询
        # 这里简化处理，实际可以直接用向量ID进行相似搜索
        results = qdrant_vector_store.search(
            query=document_id,  # 用ID作为关键词搜索
            top_k=1,
            search_mode="fulltext_only"
        )

        if not results:
            return json.dumps({
                "success": False,
                "error": f"未找到文档: {document_id}",
                "results": []
            }, ensure_ascii=False)

        # 用源文档内容进行语义搜索
        source_content = results[0].get("content", "")
        similar_results = qdrant_vector_store.search(
            query=source_content,
            top_k=top_k + 1,  # 多取一个，因为会包含自己
            search_mode="vector_only"
        )

        # 排除源文档本身
        filtered_results = [
            r for r in similar_results
            if r.get("id") != document_id
        ][:top_k]

        return json.dumps({
            "success": True,
            "source_document_id": document_id,
            "result_count": len(filtered_results),
            "results": filtered_results
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"查找相似文档失败: {e}")
        return json.dumps({
            "success": False,
            "document_id": document_id,
            "error": str(e),
            "results": []
        }, ensure_ascii=False)
